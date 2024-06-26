"""Convert a raster to h3 chunks."""

import math
from enum import Enum
from pathlib import Path
from typing import Iterator

import click
import polars as pl
import rasterio as rio
from h3ronpy.h3ronpyrs import DEFAULT_CELL_COLUMN_NAME
from h3ronpy.polars import uncompact
from h3ronpy.polars.raster import nearest_h3_resolution, raster_to_dataframe
from rasterio.windows import Window
from rich.progress import Progress, SpinnerColumn

from h3lper.cli.common import (
    MIN_TILE_LEVEL,
    RESOLUTION_TO_LEVEL_DIFF,
    make_polars_schema,
    partition_dataframe_by_tile,
    write_tiles,
)
from h3lper.models import MultiDatasetMeta


class AvailableAggFunctions(str, Enum):  # noqa: D101
    sum = "sum"
    mean = "mean"
    count = "count"  # type: ignore
    median = "median"
    mode = "mode"
    relative_area = "relative_area"


def chunk_generator(splits: int, width: int, height: int) -> Iterator[Window]:
    """Window generator for a given number of splits of a raster with width and height

    For example, using splits = 2 and raster with height and width of 512,
    will provide 4 windows of 256 as:

           256     256
        +-------+-------+
        |       |       |  256
        |       |       |
        +-------+-------+
        |       |       |  256
        |       |       |
        +-------+-------+
    """
    h_chunk_size = math.ceil(height / splits)
    w_chunk_size = math.ceil(width / splits)
    for j in range(splits):
        row_offset = j * h_chunk_size
        for i in range(splits):
            col_offset = i * w_chunk_size
            yield Window(col_offset, row_offset, w_chunk_size, h_chunk_size)


def aggregate_cells(
    df: pl.LazyFrame,
    h3res: int,
    agg_func: str,
    var_column_name: str,
    h3index_col_name: str,
) -> pl.LazyFrame:
    """Computes h3 aggregation of `df` at `h3res`.
    Returns columns in the order h3index, value.
    """
    agg_expression = pl.col(var_column_name)
    if agg_func == "sum":
        agg_expression = agg_expression.sum()
    elif agg_func == "mean":
        agg_expression = agg_expression.mean()
    elif agg_func == "count":
        agg_expression = agg_expression.count()
    elif agg_func == "median":
        agg_expression = agg_expression.median()
    elif agg_func == "mode":
        agg_expression = agg_expression.mode().first()
    elif agg_func == "relative_area":
        agg_expression = (
            (pl.col(h3index_col_name).h3.cells_area_km2() * pl.col(var_column_name)).sum()
            / pl.col("area_parent").first()
        ).cast(pl.Float64)
    else:
        raise ValueError(f"`agg_func` {agg_func} not found.")

    overview = (
        df.with_columns(
            pl.col(h3index_col_name).h3.change_resolution(h3res).alias("h3index_parent")
        )
        .group_by("h3index_parent")
        .agg(agg_expression.alias(var_column_name))
    )
    return overview.select(
        [pl.col("h3index_parent").alias(h3index_col_name), pl.col(var_column_name)]
    )


def make_overviews(
    base_level_path: Path,
    output_path: Path,
    overview_level: int,
    agg_func: str,
    var_name: str,
    progress: Progress,
    meta: dict,
) -> None:
    """Compute higher resolution tiles with agg function `agg_func`."""

    overview_resolution = overview_level + RESOLUTION_TO_LEVEL_DIFF
    seen_tiles = set()
    min_value = math.inf
    max_value = 0
    n_cells = 0

    tiles = list(base_level_path.glob("*.arrow"))

    iter_tiles_task = progress.add_task(f"[cyan]Processing tiles for level {overview_level}")
    for tile in progress.track(tiles, task_id=iter_tiles_task):
        progress.update(iter_tiles_task)
        df = pl.scan_ipc(tile, memory_map=True)
        df = aggregate_cells(
            df,
            overview_resolution,
            agg_func,
            var_name,
            h3index_col_name=DEFAULT_CELL_COLUMN_NAME,
        ).with_columns(
            pl.col(DEFAULT_CELL_COLUMN_NAME).h3.change_resolution(overview_level).alias("tile_id")
        )

        max_value = max(max_value, df.select(var_name).max().collect().item())
        min_value = min(min_value, df.select(var_name).min().collect().item())

        partition_dfs = df.collect().partition_by(["tile_id"], as_dict=True, include_key=False)
        for tile_group, tile_df in partition_dfs.items():
            if tile_df.shape[0] == 0:  # todo: skip empty tiles ?
                continue
            tile_id = tile_group[0]
            filename = output_path / (hex(tile_id)[2:] + ".arrow")
            if tile_id in seen_tiles:
                tile_df = pl.concat(
                    [pl.read_ipc(filename), tile_df], how="vertical_relaxed"
                ).unique(subset=["cell"])
                tile_df.write_ipc(filename)
                n_cells += len(tile_df)
            else:
                seen_tiles.add(tile_id)
                tile_df.write_ipc(filename)
                n_cells += len(tile_df)

    meta["datasets"][0]["legend"]["stats"].append(
        {"level": overview_level, "max": max_value, "min": min_value}
    )
    progress.console.print(
        f"+ Level {overview_level} -> {len(seen_tiles)} tiles -> {n_cells} H3 cells"
    )
    progress.update(iter_tiles_task, visible=False)


def raster_to_h3(
    h3_res: int | None,
    input_file: Path,
    nodata: int | float,
    output_path: Path,
    splits: int,
    var_name: str,
    compact_filtering: bool,
    meta: dict,
    progress: Progress,
) -> tuple[Path, int]:
    """Raster file to h3 arrow tiles at finest resolution

    :returns:
        tuple(base_level_path, base_tile_level)
    """

    seen_tiles: set[int] = set()

    with rio.open(input_file) as src:
        h3_res = h3_res if h3_res is not None else nearest_h3_resolution(src.shape, src.transform)
        # Resolution of the tile index. A tile is a h3 cell that contains all the
        # cells that are RESOLUTION_TO_LEVEL_DIFF resolutions below it.
        base_tile_level = h3_res - RESOLUTION_TO_LEVEL_DIFF
        nodata = nodata if nodata is not None else int(src.nodata)
        meta["datasets"][0].update(
            {
                "var_name": var_name,
                "var_dtype": src.dtypes[0],
                "lineage": [str(input_file)],
                "nodata": nodata,
                "description": "",
            }
        )

        base_level_path = output_path / str(base_tile_level)
        base_level_path.mkdir(exist_ok=True, parents=True)

        max_value = 0
        min_value = math.inf
        n_cells = 0
        progress.console.print(
            f"Converting to h3 resolution {h3_res}. Tiling at level {base_tile_level}\n"
        )
        read_chunk_task = progress.add_task("[cyan]Processing part...", total=None)
        for i, window in enumerate(chunk_generator(splits, src.width, src.height)):
            progress.update(
                read_chunk_task,
                description=f"[cyan]Processing part {i + 1}/{splits ** 2}...",
                total=splits**2,
            )
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            df = raster_to_dataframe(
                data,
                win_transform,
                h3_res,
                nodata_value=nodata,
                compact=compact_filtering,
            ).lazy()

            if compact_filtering:
                df = (
                    df.filter(pl.col("value") > 0)
                    .with_columns(
                        pl.col(DEFAULT_CELL_COLUMN_NAME).map_elements(
                            lambda x: uncompact([x], h3_res),
                            return_dtype=pl.List(pl.UInt64),
                        )
                    )
                    .explode("cell")
                )

            df = df.rename({"value": var_name})
            df = df.cast(make_polars_schema(meta["datasets"])).collect()

            max_value = max(max_value, df.select(var_name).max().item())
            min_value = min(min_value, df.select(var_name).min().item())
            n_cells += len(df)

            partition_dfs = partition_dataframe_by_tile(df, base_tile_level)

            write_tiles(
                partition_dfs,
                progress,
                seen_tiles,
                base_level_path,
            )
            progress.update(read_chunk_task, advance=1)

    meta["datasets"][0].update(
        {
            "legend": {
                "legend_type": "continuous",
                "stats": [{"level": base_tile_level, "max": max_value, "min": min_value}],
            }
        }
    )
    progress.console.print(
        f"+ Level {base_tile_level} -> {len(seen_tiles)} tiles -> {n_cells} H3 cells"
    )
    return base_level_path, base_tile_level


@click.command(name="raster")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--var-name", required=True, help="Column name in the arrow ipc")
@click.option("--nodata", help="Use this nodata instead of internal value")
@click.option(
    "--agg-func",
    type=click.Choice([func.name for func in AvailableAggFunctions], case_sensitive=False),
    default=AvailableAggFunctions.mean.name,
    help="Overview aggregation function.",
)
@click.option(
    "--splits",
    default=0,
    type=int,
    help="Divide and process the raster in chunks to reduce the memory usage.",
)
@click.option("--h3-res", type=int, help="Output h3 resolution.")
@click.option(
    "--compact", is_flag=True, help="Use compact to reduce memory footprint at cost of speed."
)
@click.option("--use-hex", is_flag=True, help="Use hexadecimal h3 index representation")
def main(
    input_file: Path,
    output_path: Path,
    var_name: str,
    nodata: int,
    agg_func: str,
    splits: int,
    h3_res: int | None,
    compact: bool,
    use_hex: bool,
) -> None:
    """Convert a raster dataset to a h3 tiled dataset."""
    progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), transient=True)
    with progress:
        meta = {"datasets": [{}], "h3_grid_info": [{}]}  # type: ignore

        base_level_path, base_tile_level = raster_to_h3(
            h3_res,
            input_file,
            nodata,
            output_path,
            splits,
            var_name,
            compact,
            meta,
            progress,
        )

        meta["h3_grid_info"][0].update(
            {"level": base_tile_level, "h3_cells_resolution": 6, "h3_cells_count": 100}
        )

    # ----------------------------------------------------------
    #                    MAKE OVERVIEWS
    # ----------------------------------------------------------

    progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), transient=True)
    with progress:
        current_tile_path = base_level_path
        next_tile_level = base_tile_level - 1
        while next_tile_level >= MIN_TILE_LEVEL:
            overview_path = output_path / str(next_tile_level)
            overview_path.mkdir(exist_ok=True)

            make_overviews(
                current_tile_path,
                overview_path,
                next_tile_level,
                agg_func,
                var_name,
                progress,
                meta,
            )

            next_tile_level -= 1
            current_tile_path = overview_path

        meta["datasets"][0].update({"aggregation_method": agg_func})

        with open(output_path / "meta.json", "w") as meta_file:
            meta_file.write(MultiDatasetMeta(**meta).model_dump_json(indent=2))  # type: ignore

        progress.console.print("Done!")


if __name__ == "__main__":
    main()
