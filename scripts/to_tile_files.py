"""Convert a raster to h3 chunks."""
from enum import Enum
from pathlib import Path
from typing import Annotated

import polars as pl
import rasterio as rio
import typer
from h3ronpy.polars.raster import nearest_h3_resolution, raster_to_dataframe
from raster_to_h3 import aggregate_cells, chunk_generator
from rich import print
from rich.progress import track


class AvailableAggFunctions(str, Enum):  # noqa: D101
    sum = "sum"
    mean = "mean"
    count = "count"  # type: ignore
    relative_area = "relative_area"


def to_parquet_files(
    input_file: Path,
    output_path: Path,
    nodata: Annotated[int, typer.Option(help="Set nodata value.")] = 0,
    agg_func: Annotated[
        AvailableAggFunctions, typer.Option(help="Overview aggregation function.")
    ] = AvailableAggFunctions.mean,
    splits: Annotated[
        int, typer.Option(help="Dive and process the raster in chunks to reduce the memory usage.")
    ] = 2,
    use_hex: Annotated[bool, typer.Option(help="Output h3 index as hex string.")] = False,
) -> None:
    """Convert a raster to a h3 file."""
    seen_tiles = set()

    with rio.open(input_file) as src:
        h3res = nearest_h3_resolution(src.shape, src.transform)
        print(f"Will process {splits ** 2} chunks at h3 resolution {h3res}")

        # iterate over raster chunks
        for i, (_, window) in enumerate(chunk_generator(splits, src.height, src.width)):
            print(f"Processing chunk {i + 1}/{splits ** 2} ...")
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            nodata = nodata if nodata is not None else src.nodata
            df = raster_to_dataframe(
                data,
                win_transform,
                h3res,
                nodata_value=nodata,
                compact=False,
            )

            # Resolution of the tile index. A tile is a h3 cell that contains all the cells
            # that are 5 resolutions below it.
            tile_index_res = h3res - 5

            df = (
                df.with_columns(pl.col("cell").h3.change_resolution(tile_index_res).alias("tile"))
                .filter(pl.col("value") > 0)
                .unique(subset=["cell"])
            )
            if use_hex:
                df = df.with_columns(
                    pl.col("cell").cast(pl.Utf8).h3.cells_parse().h3.cells_to_string()
                )
            while tile_index_res >= 0:
                overview_res = tile_index_res + 5

                if (
                    overview_res < h3res
                ):  # aggregate to correct overview resolution if not the first write
                    print(f"Aggregating to resolution {overview_res}")
                    df = aggregate_cells(
                        df, overview_res, agg_func.value, h3index_col_name="cell"
                    ).with_columns(
                        pl.col("cell").h3.change_resolution(tile_index_res).alias("tile")
                    )

                overview_output_path = output_path / str(tile_index_res)
                overview_output_path.mkdir(exist_ok=True, parents=True)

                # make tiles
                partition_dfs = df.partition_by("tile", as_dict=True, include_key=False)

                for tile_id, tile_df in track(partition_dfs.items(), description="Writing tiles"):
                    if tile_df.shape[0] == 0:  # todo: skip empty tiles ?
                        continue
                    filename = overview_output_path / (hex(tile_id)[2:] + ".arrow")
                    if tile_id in seen_tiles:
                        pl.concat([pl.read_ipc(filename), tile_df]).unique(
                            subset=["cell"]
                        ).write_ipc(filename)
                    else:
                        tile_df.write_ipc(filename)
                    seen_tiles.add(tile_id)

                tile_index_res -= 1


if __name__ == "__main__":
    typer.run(to_parquet_files)
