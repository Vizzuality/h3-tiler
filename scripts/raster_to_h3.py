"""
Author: Biel Stela

Script to convert raster to h3 files
"""
from math import ceil
from pathlib import Path
from typing import Iterator, Optional

import click
import polars as pl
import rasterio as rio
from h3ronpy.polars.raster import nearest_h3_resolution, raster_to_dataframe
from rasterio.windows import Window

AVAILABLE_AGG_FUNCTIONS = ("sum", "mean", "count", "relative_area")


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
@click.option(
    "--agg",
    type=click.Choice(AVAILABLE_AGG_FUNCTIONS),
    default="mean",
    help="Aggregation method used to compute overviews.",
)
@click.option("--nodata", type=int, help="Force to use this nodata value")
def main(
    input_file: Path,
    output_file: Path,
    splits: int,
    compact: bool,
    last_overview: Optional[int],
    agg: str,
    nodata: Optional[int],
):
    """Convert a raster to a h3 file."""
    with rio.open(input_file) as src:
        h3res = nearest_h3_resolution(src.shape, src.transform)
        click.echo(f"Converting to H3 with resolution: {h3res}")

    if splits > 1:
        raster_to_h3_windowed(input_file, output_file, splits, compact, h3res, nodata)
        if last_overview:
            build_overviews_by_level(output_file, agg, h3res, last_overview)

    else:
        with rio.open(input_file) as src:
            df = raster_to_dataframe(
                src.read(1),
                src.transform,
                h3res,
                nodata_value=nodata or src.nodata,
                compact=compact,
            ).lazy()

        df = clean_dataframe(df)
        if last_overview:
            df = build_overviews(agg, df, h3res, last_overview)
        df.collect().write_csv(output_file)


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


def raster_to_h3_windowed(
    input_file: Path,
    out_file: Path,
    splits: int,
    compact: bool,
    h3res: int,
    user_nodata: Optional[int],
):
    """Convert a raster to LazyFrame of h3 cell -> value pairs.

    Since the function used (h3ronpy's raster_to_dataframe) is fully parallel, a large raster
    can fill all the memory easily. This iterates the raster by smaller blocks and writes them to disk.
    """
    out_file.unlink(missing_ok=True)
    with rio.open(input_file) as src:
        click.echo(f"Will process {splits**2} blocks.")
        for ji, window in chunk_generator(splits, src.height, src.width):
            click.echo(f"Processing block {ji}...")
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            nodata = user_nodata if user_nodata is not None else src.nodata
            df = raster_to_dataframe(
                data,
                win_transform,
                h3res,
                nodata_value=nodata,
                compact=compact,
            ).lazy()
            df = clean_dataframe(df)
            df = df.collect().to_pandas()
            df.to_csv(out_file, mode="a", index=False, header=False)


def aggregate_cells(
    df: pl.LazyFrame, h3res: int, agg_func: str, h3index_col_name: str = "h3index"
) -> pl.LazyFrame:
    """Computes h3 aggregation of `df` at `h3res`.
    Returns columns in the order h3index, value.
    """
    agg_expression = pl.col("value")
    match agg_func:
        case "sum":
            agg_expression = agg_expression.sum()
        case "mean":
            agg_expression = agg_expression.mean()
        case "count":
            agg_expression = agg_expression.count()
        case "relative_area":
            agg_expression = (
                (pl.col("h3index").h3.cells_area_km2() * pl.col("value")).sum()
                / pl.col("area_parent").first()
            ).cast(pl.Float64)
        case _:
            raise ValueError(f"`agg_func` {agg_func} not found.")

    overview = (
        df.with_columns(
            pl.col(h3index_col_name).h3.change_resolution(h3res).alias("h3index_parent")
        )
        .with_columns(pl.col("h3index_parent").h3.cells_area_km2().alias("area_parent"))
        .group_by("h3index_parent")
        .agg(value=agg_expression)
    )
    return overview.select([pl.col("h3index_parent").alias(h3index_col_name), pl.col("value")])


def build_overviews(  # noqa: D103
    agg: str, df: pl.LazyFrame | pl.DataFrame, h3res: int, last_overview: int
) -> pl.LazyFrame | pl.DataFrame:
    overviews = [df]
    click.echo("building overviews...")
    for _i, overview_res in enumerate(range(h3res - 1, last_overview - 1, -1)):
        overviews.append(aggregate_cells(overviews[-1], overview_res, agg))
    df = pl.concat(overviews)
    return df


def build_overviews_by_level(base_overview_file: Path, agg: str, h3res: int, last_overview: int):
    """Build overviews step by step starting from the base overview file and following with lower resolutions until
    `last_overview` is reached.
    """
    for i, overview_res in enumerate(range(h3res - 1, last_overview - 1, -1)):
        click.echo(f"Building overview {overview_res}...")
        previous_overview = (
            base_overview_file.parent / f"{base_overview_file.stem}_{overview_res + 1}.csv"
        )
        df = aggregate_cells(
            pl.scan_csv(
                # use the base resolution file in the first iteration.
                previous_overview if i > 0 else base_overview_file,
                new_columns=["h3index", "value"],
                dtypes=[pl.UInt64],
            ),
            overview_res,
            agg,
        )
        output_file = base_overview_file.parent / f"{base_overview_file.stem}_{overview_res}.csv"
        df = df.collect()
        # NOTE: This is ugly and writes twice, once to a single overview file to read in the loop
        # and followed by and append to the main output file.
        df.write_csv(output_file)  # write new intermediate file
        df.to_pandas().to_csv(
            base_overview_file, mode="a", index=False, header=False
        )  # append to base file
        if i > 0:
            previous_overview.unlink()  # remove used intermediate file
        del df


def clean_dataframe(
    df: pl.LazyFrame | pl.DataFrame,
) -> pl.LazyFrame | pl.DataFrame:
    """Clean dataframe from nulls and duplicates."""
    df = df.drop_nulls()
    df = df.rename({"cell": "h3index"})
    df = df.filter(pl.col("value") > 0)
    df = df.unique(subset=["h3index"])
    # reorder columns to be "index like" h3index -> value.
    df = df.select([pl.col("h3index"), pl.col("value")])
    return df


if __name__ == "__main__":
    main()
