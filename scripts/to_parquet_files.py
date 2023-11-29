"""Convert a raster to h3 chunks."""
from pathlib import Path
from typing import Optional

import polars as pl
import rasterio as rio
import typer
from h3ronpy.polars.raster import nearest_h3_resolution, raster_to_dataframe
from raster_to_h3 import (
    chunk_generator,
)
from rich.progress import track

app = typer.Typer()


@app.command()
def to_parquet_files(
    input_file: Path,
    output_path: Path,
    nodata: Optional[int] = None,
    last_overview: Optional[int] = 5,
    agg_func: Optional[str] = "sum",
    chunk_size: int = 2,
) -> None:
    """Convert a raster to a h3 file."""
    output_path.mkdir(exist_ok=True, parents=True)
    seen_tiles = set()

    with rio.open(input_file) as src:
        h3res = nearest_h3_resolution(src.shape, src.transform)
        tile_index_res = h3res - 5
        typer.echo(f"Will process {chunk_size**2} blocks with resolution: {h3res}")
        # make a temp file
        for ji, window in chunk_generator(chunk_size, src.height, src.width):
            typer.echo(f"Processing block {ji}...")
            data = src.read(1, window=window)
            win_transform = src.window_transform(window)
            nodata = nodata if nodata is not None else src.nodata

            df = raster_to_dataframe(
                data,
                win_transform,
                h3res,
                nodata_value=nodata,
                compact=False,
            ).lazy()

            df = (
                df.with_columns(pl.col("cell").h3.change_resolution(tile_index_res).alias("parent"))
                .filter(pl.col("value") > 0)
                .unique(subset=["cell"])
            )

            partition_dfs = df.collect().partition_by("parent", as_dict=True, include_key=False)
            for tile_id, df in track(partition_dfs.items(), description="Writing tiles"):
                if df.shape[0] == 0:  # skip empty tiles
                    continue
                filename = output_path / (hex(tile_id)[2:] + ".parquet")
                if tile_id in seen_tiles:
                    pl.concat([pl.read_parquet(filename), df]).unique(
                        subset=["cell"]
                    ).write_parquet(filename)
                else:
                    df.write_parquet(filename)
                seen_tiles.add(tile_id)


if __name__ == "__main__":
    app()
