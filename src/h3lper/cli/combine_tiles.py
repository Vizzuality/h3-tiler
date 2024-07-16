"""
Tiles must have unique column names and be folders with the format:
```
.
└── tile
    ├── 0
    │   ├── 80a9fffffffffff.arrow
    │   ├── 80b3fffffffffff.arrow
    │   └── ...
    ├── 1
    ├── 2
    └── ...
```
"""

from pathlib import Path

import click
import numpy as np
import polars as pl
from rich.progress import Progress, SpinnerColumn

from h3lper.cli.common import make_polars_schema
from h3lper.models import MultiDatasetMeta


def check_dataset_format(tile_source: Path) -> None:
    """Simple sanity check to ensure that all tile sources are valid."""
    if not tile_source.exists():
        raise FileNotFoundError
    if tile_source.is_file():
        raise ValueError("Tile source should be directory")
    # TODO: Check that tiles are correct format.
    files = []
    for d in tile_source.iterdir():
        if d.is_dir():
            try:
                int(d.name)
            except ValueError as e:
                raise ValueError("Folders in tile source should be integers") from e
        else:
            files.append(d.name)

    if "meta.json" not in files:
        raise ValueError(f"Dataset {tile_source} does not have meta file.")
        # TODO: Check meta schema


def dataset_minmax_level(tile_source: Path) -> tuple[int, int]:
    """Min and max level of tile source."""
    levels = [int(d.name) for d in tile_source.iterdir() if d.is_dir()]
    return min(levels), max(levels)


def merge_metadata(metas: list[MultiDatasetMeta]) -> MultiDatasetMeta:
    """Merge datasets metadata into a single one"""
    datasets = [d for m in metas for d in m.datasets]
    # for dataset in datasets:
    #     if isinstance(dataset.legend, CategoricalLegend):
    #         pass
    #     else:
    #         pass
    grid_infos = metas[0].h3_grid_info
    return MultiDatasetMeta(datasets=datasets, h3_grid_info=grid_infos)


@click.command(name="combine")
@click.argument("datasets", type=click.Path(exists=True, path_type=Path), nargs=-1)
@click.argument("out_path", type=click.Path(path_type=Path))
@click.option("--random-columns", type=int, help="Append n random variables for testing purposes")
def main(datasets: list[Path], out_path: Path, random_columns: int) -> None:
    """Combine different tile sources to a single one.

    The maximum level of tiling of the resulting dataset will be set
    by the dataset with the minimum number of levels. Same for the minimum
    level. Tiles that are only present in one dataset will have only
    one non-null column and the rest will be null values.
    """

    progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), transient=True)
    with progress:
        metas = []
        common_min_level = 0
        common_max_level = 99
        datasets_to_trim = []
        for dataset in datasets:
            check_dataset_format(dataset)
            min_tile_level, max_tile_level = dataset_minmax_level(dataset)
            common_min_level = max(common_min_level, min_tile_level)
            common_max_level = min(common_max_level, max_tile_level)
            if common_max_level < max_tile_level:
                datasets_to_trim.append((dataset, max_tile_level - common_max_level))
            elif common_min_level > min_tile_level:
                datasets_to_trim.append((dataset, common_min_level - common_min_level))
            with open(dataset / "meta.json") as f:
                metas.append(MultiDatasetMeta.model_validate_json(f.read()))

        meta = merge_metadata(metas)
        progress.console.print(f"Combining {len(datasets)} datasets")

        if datasets_to_trim:
            progress.console.print(
                "\n[bold yellow]Warning:[/bold yellow]",
                "Datasets have [bold white]different depths[/bold white]."
                f" Common levels go from {common_max_level} to {common_min_level}",
            )
            for f, n in datasets_to_trim:  # type: ignore
                progress.console.print(f"  + {str(f)} looses {n} level/s")
            progress.console.print("\n")

        for level in range(common_min_level, common_max_level + 1):
            tiles = set()
            for dataset in datasets:
                tiles.update([f.name for f in (dataset / str(level)).glob("*.arrow")])

            for tile_name in progress.track(tiles, description=f"Combining level {level}"):
                # first dataframe is empty just to set the typing for the concat
                dfs = [pl.DataFrame(schema=make_polars_schema(meta.model_dump()["datasets"]))]
                for dataset in datasets:
                    tile_file = dataset / str(level) / tile_name
                    if not tile_file.exists():
                        continue
                    dfs.append(pl.read_ipc(tile_file))
                tile_df = pl.concat(dfs, how="diagonal_relaxed", parallel=True)
                # oneliner to stack repeated cell indices in the way:
                # ┌──────┬──────┬──────┐
                # │ cell ┆ b    ┆ c    │
                # │ ---  ┆ ---  ┆ ---  │         ┌──────┬──────┬─────┐
                # │ u64  ┆ f32  ┆ str  │         │ cell ┆ b    ┆ c   │
                # ╞══════╪══════╪══════╡         │ ---  ┆ ---  ┆ --- │
                # │ 1    ┆ 9.0  ┆ null │         │ u64  ┆ f32  ┆ str │
                # │ 2    ┆ 9.0  ┆ null │         ╞══════╪══════╪═════╡
                # │ 3    ┆ 9.0  ┆ null │         │ 1    ┆ 9.0  ┆ a   │
                # │ 1    ┆ null ┆ a    │   ==>   │ 2    ┆ 9.0  ┆ b   │
                # │ 2    ┆ null ┆ b    │         │ 3    ┆ 9.0  ┆ c   │
                # │ 3    ┆ null ┆ c    │         │ 4    ┆ null ┆ a   │
                # │ 4    ┆ null ┆ a    │         │ 5    ┆ null ┆ b   │
                # │ 5    ┆ null ┆ b    │         │ 6    ┆ null ┆ c   │
                # │ 6    ┆ null ┆ c    │         └──────┴──────┴─────┘
                # └──────┴──────┴──────┘
                # There must be a more idiomatic way to do this. We can safely use max because there
                # must be only one none null value in each group
                tile_df = tile_df.group_by("cell", maintain_order=True).agg(pl.all().max())
                out_dataset_path = out_path / str(level)
                out_dataset_path.mkdir(parents=True, exist_ok=True)
                if random_columns:
                    for i in range(random_columns):
                        tile_df = tile_df.with_columns(
                            pl.lit(np.random.rand(tile_df.height)).alias(f"random_{i}")
                        )
                tile_df.write_ipc(out_dataset_path / tile_name)

            # progress.console.print(f"+ Done level {level}")

        with open(out_path / "meta.json", "w") as f:
            f.write(meta.model_dump_json(indent=2))

        progress.console.print("Done!")


if __name__ == "__main__":
    main()
