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
from rich import print
from rich.progress import Progress, SpinnerColumn

from h3lper.models import MultiDatasetMeta

MIN_TILE_LEVEL = 0
RESOLUTION_TO_LEVEL_DIFF = 5


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
    if splits == 0:
        yield Window(0, 0, width, height)
        return
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
    var_column_name: str,
    progress: Progress,
    meta: dict,
) -> None:
    """Compute higher resolution tiles with agg function `agg_func`."""
    tiles = list(base_level_path.glob("*.arrow"))
    overview_resolution = overview_level + RESOLUTION_TO_LEVEL_DIFF
    seen_tiles = set()
    iter_tiles_task = progress.add_task("Processing tile: ")
    min_value = math.inf
    max_value = 0
    for tile in progress.track(tiles, task_id=iter_tiles_task):
        progress.update(iter_tiles_task, description=f"Processing tile: {tile.stem}")
        df = pl.scan_ipc(tile, memory_map=True)
        df = aggregate_cells(
            df,
            overview_resolution,
            agg_func,
            var_column_name,
            h3index_col_name=DEFAULT_CELL_COLUMN_NAME,
        ).with_columns(
            pl.col(DEFAULT_CELL_COLUMN_NAME).h3.change_resolution(overview_level).alias("tile_id")
        )

        max_value = max(max_value, df.select(var_column_name).max().collect().item())
        min_value = min(min_value, df.select(var_column_name).min().collect().item())

        partition_dfs = df.collect().partition_by(["tile_id"], as_dict=True, include_key=False)
        for tile_group, tile_df in partition_dfs.items():
            if tile_df.shape[0] == 0:  # todo: skip empty tiles ?
                continue
            tile_id = tile_group[0]
            filename = output_path / (hex(tile_id)[2:] + ".arrow")
            if tile_id in seen_tiles:
                pl.concat([pl.read_ipc(filename), tile_df], how="vertical_relaxed").unique(
                    subset=["cell"]
                ).write_ipc(filename)
            else:
                seen_tiles.add(tile_id)
                tile_df.write_ipc(filename)
    meta["datasets"][0]["legend"]["stats"].append(
        {"level": overview_level, "max": max_value, "min": min_value}
    )
    progress.update(iter_tiles_task, visible=False)
    print(
        f"Computed {len(seen_tiles)} overview tiles at resolution {overview_resolution}."  # noqa E501
    )


def raster_to_h3(
    h3_res: int | None,
    input_file: Path,
    nodata: int | float,
    output_path: Path,
    splits: int,
    var_name: str,
    compact_filtering: bool,
    meta: dict,
) -> tuple[Path, int]:
    """Raster file to h3 arrow tiles at finest resolution

    :returns:
        tuple(base_level_path, base_tile_level, dataset_metadata)
    """
    seen_tiles = set()
    n_chunks = splits**2
    progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), transient=True)
    progress.start()
    read_chunk_task = progress.add_task("[cyan]Sampling raster to h3...", total=n_chunks)
    with rio.open(input_file) as src:
        h3_res = h3_res if h3_res is not None else nearest_h3_resolution(src.shape, src.transform)
        # Resolution of the tile index. A tile is a h3 cell that contains all the
        # cells that are RESOLUTION_TO_LEVEL_DIFF resolutions below it.
        base_tile_level = h3_res - RESOLUTION_TO_LEVEL_DIFF

        meta["datasets"][0].update(
            {
                "var_name": var_name,
                "var_dtype": src.dtypes[0],
                "lineage": [str(input_file)],
                "description": "",
            }
        )

        base_level_path = output_path / str(base_tile_level)
        base_level_path.mkdir(exist_ok=True, parents=True)
        max_value = 0
        min_value = math.inf
        for i, window in enumerate(chunk_generator(splits, src.width, src.height)):
            progress.update(
                read_chunk_task, description=f"[cyan]Processing part {i + 1}/{n_chunks}..."
            )
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            nodata = nodata if nodata is not None else src.nodata
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
                        pl.col("cell").map_elements(
                            lambda x: uncompact([x], h3_res),
                            return_dtype=pl.List(pl.UInt64),
                        )
                    )
                    .explode("cell")
                )

            df = (
                df.rename({"value": var_name})
                .with_columns(
                    pl.col(DEFAULT_CELL_COLUMN_NAME)
                    .h3.change_resolution(base_tile_level)
                    .alias("tile_id")
                )
                .unique(subset=[DEFAULT_CELL_COLUMN_NAME])
            )

            max_value = max(max_value, df.select(var_name).max().collect().item())
            min_value = min(min_value, df.select(var_name).min().collect().item())

            partition_dfs = df.collect().partition_by(["tile_id"], as_dict=True, include_key=False)

            write_tiles_task = progress.add_task("Writing tiles")

            for tile_group, tile_df in progress.track(
                partition_dfs.items(), task_id=write_tiles_task
            ):
                tile_id = tile_group[0]
                filename = base_level_path / (hex(tile_id)[2:] + ".arrow")
                progress.update(write_tiles_task, description=f"Writing tile {filename.stem}")
                if tile_id in seen_tiles:
                    pl.concat([pl.read_ipc(filename), tile_df]).unique(
                        subset=[DEFAULT_CELL_COLUMN_NAME]
                    ).write_ipc(filename)
                else:
                    tile_df.write_ipc(filename)
                seen_tiles.add(tile_id)
            progress.update(write_tiles_task, visible=False)
            progress.update(read_chunk_task, advance=1)

    meta["datasets"][0].update(
        {
            "legend": {
                "legend_type": "continuous",
                "stats": [{"level": base_tile_level, "max": max_value, "min": min_value}],
            }
        }
    )

    progress.stop()
    print(f"Converted {input_file} to {len(seen_tiles)} h3 tiles with resolution {h3_res}.")
    return base_level_path, base_tile_level


@click.command(name="tile")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--var_column_name", required=True, help="Column name in the arrow ipc")
@click.option("--nodata", default=0, help="Set nodata value.")
@click.option(
    "--agg_func",
    type=click.Choice([func.name for func in AvailableAggFunctions], case_sensitive=False),
    default=AvailableAggFunctions.mean.name,
    help="Overview aggregation function.",
)
@click.option(
    "--splits", default=0, help="Dive and process the raster in chunks to reduce the memory usage."
)
@click.option("--h3_res", type=int, help="Output h3 resolution.")
@click.option(
    "--compact", is_flag=True, help="Use compact to reduce memory footprint at cost of speed."
)
def main(
    input_file: Path,
    output_path: Path,
    var_column_name: str,
    nodata: int,
    agg_func: str,
    splits: int,
    h3_res: int | None,
    compact: bool,
) -> None:
    """Convert a raster dataset to a h3 tiled dataset."""

    meta = {"datasets": [{}], "h3_grid_info": [{}]}  # type: ignore

    base_level_path, base_tile_level = raster_to_h3(
        h3_res, input_file, nodata, output_path, splits, var_column_name, compact, meta
    )

    meta["h3_grid_info"][0].update(
        {"level": base_tile_level, "h3_cells_resolution": 6, "h3_cells_count": 100}
    )

    # ----------------------------------------------------------
    #                    MAKE OVERVIEWS
    # ----------------------------------------------------------

    progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), transient=True)
    progress.start()
    total_computing_overviews_task = progress.add_task(
        "[cyan]Computing overviews ...", total=base_tile_level - 1
    )

    current_tile_path = base_level_path
    next_tile_level = base_tile_level - 1
    while next_tile_level >= MIN_TILE_LEVEL:
        overview_path = output_path / str(next_tile_level)
        overview_path.mkdir(exist_ok=True)

        progress.update(
            total_computing_overviews_task,
            description=f"Computing overview {overview_path}",
        )

        make_overviews(
            current_tile_path,
            overview_path,
            next_tile_level,
            agg_func,
            var_column_name,
            progress,
            meta,
        )

        next_tile_level -= 1
        current_tile_path = overview_path

        progress.update(total_computing_overviews_task, advance=1)
    progress.stop()

    meta["datasets"][0].update({"aggregate_method": agg_func})

    with open(output_path / "meta.json", "w") as meta_file:
        meta_file.write(MultiDatasetMeta(**meta).model_dump_json(indent=2))  # type: ignore


if __name__ == "__main__":
    main()
