from pathlib import Path

import click
import geopandas as gpd
from h3ronpy.pandas.vector import geodataframe_to_cells
from rich.progress import Progress, SpinnerColumn

from h3lper.cli.common import RESOLUTION_TO_LEVEL_DIFF, partition_dataframe_by_tile, write_tiles


@click.command(name="vector")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--resolution" "-r", type=int, help="H3 resolution")
def main(input_file: Path, output_path: Path, resolution: int):
    """Convert a vector dataset to a h3 tiled dataset."""
    tile_level = resolution - RESOLUTION_TO_LEVEL_DIFF

    seen_tiles: set[int] = set()

    df = gpd.read_file(input_file, engine="pyogrio")
    h3df = geodataframe_to_cells(df, resolution=resolution)

    parts = partition_dataframe_by_tile(h3df, tile_level)

    progress = Progress(SpinnerColumn(), *Progress.get_default_columns(), transient=True)
    with progress:
        write_tiles(parts, progress, seen_tiles, Path(""))


if __name__ == "__main__":
    main()
