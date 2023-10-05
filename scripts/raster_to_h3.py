"""
Author: Biel Stela

Script to convert raster to h3 files
"""
import time
from math import ceil
from pathlib import Path
from typing import Iterator

import click
import polars as pl
import rasterio as rio
from h3ronpy.polars import change_resolution
from h3ronpy.polars.raster import nearest_h3_resolution, raster_to_dataframe
from rasterio.windows import Window


def chunk_generator(splits: int, height: int, width: int) -> Iterator[Window]:
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

    h_chunk_size = ceil(height / splits)
    w_chunk_size = ceil(width / splits)
    for j in range(splits):
        row_offset = j * h_chunk_size
        for i in range(splits):
            col_offset = i * w_chunk_size
            yield (i, j), Window(col_offset, row_offset, w_chunk_size, h_chunk_size)


def raster_to_h3_windowed(input_file: Path, splits: int, compact: bool, h3res: int) -> pl.LazyFrame:
    """Convert a raster to LazyFrame of h3 cell -> value pairs.

    Since the function used (h3ronpy's raster_to_dataframe) is fully parallel, a large raster
    can fill all the memory easily. So here this iterates the raster by smaller blocks.
    """
    with rio.open(input_file) as src:
        dfs = []
        for ji, window in chunk_generator(splits, src.height, src.width):
            click.echo(f"Processing block {ji}...")
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            dfs.append(
                raster_to_dataframe(
                    data, win_transform, h3res, nodata_value=src.nodata, compact=compact
                ).lazy()
            )
    df = pl.concat(dfs, how="vertical")
    return df


def compute_overviews(df: pl.LazyFrame, h3res: int, agg_func: str) -> pl.LazyFrame:
    """Compute h3 overviews from original resolution up to `last_overview`."""
    agg_expression = pl.col("value")
    match agg_func:
        case "sum":
            agg_expression = agg_expression.sum
        case "mean":
            agg_expression = agg_expression.mean
        case _:
            raise ValueError(f"`agg_func` {agg_func} not found. Must be one of [sum, mean]")
    overview = (
        df.with_columns(
            pl.col("h3index").map_batches(lambda x: change_resolution(x, h3res)).alias("h3index")
        )
        .group_by("h3index")
        .agg(agg_expression())
    )
    return overview.select([pl.col("h3index"), pl.col("value")])


@click.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "--splits",
    type=click.INT,
    default=0,
    help="Split the raster and process each block sequentially. Useful for large datasets that don't fit in memory.",
)
@click.option(
    "--compact",
    is_flag=True,
    help="Generate compact H3.",
)
@click.option(
    "--last-overview",
    "-lo",
    type=click.INT,
    help="Last resolution for wich will an overview be computed.",
)
@click.option("--agg", default="sum", help="Aggregation method used to compute overviews.")
def main(
    input_file: Path,
    output_file: Path,
    splits: int,
    compact: bool,
    last_overview: int | None,
    agg: str,
):
    """Convert a raster to a h3 file."""
    with rio.open(input_file) as src:
        h3res = nearest_h3_resolution(src.shape, src.transform)
        click.echo(f"Converting to H3 with resolution: {h3res}")

    if splits > 1:
        df = raster_to_h3_windowed(input_file, splits, compact, h3res)
    else:
        with rio.open(input_file) as src:
            df = raster_to_dataframe(
                src.read(1), src.transform, h3res, nodata_value=src.nodata, compact=compact
            ).lazy()

    df = df.drop_nulls()
    df = df.rename({"cell": "h3index"})
    df = df.filter(pl.col("value") > 0)
    df = df.unique(subset=["h3index"])
    # Convert to hex representation (needed in h3 functions). This is slow af but currently
    # there's no way to format natively in polars: https://github.com/pola-rs/polars/issues/7133
    # df = df.with_columns(pl.col("h3index").map_elements(lambda x: hex(x)[2:]))
    # reorder columns to be "index like" h3index -> value.
    df = df.select([pl.col("h3index"), pl.col("value")])
    time.sleep(5)
    if last_overview:
        overview_resolutions = list(range(h3res - 1, last_overview - 1, -1))
        for overview_res in overview_resolutions:
            click.echo(f"Building overview {overview_res}...")
            overview = compute_overviews(df, overview_res, agg)
            overview.sink_csv(output_file.with_name(f"{output_file.stem}_{overview_res}.csv"))
    df.sink_csv(output_file)


if __name__ == "__main__":
    main()
