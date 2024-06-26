import click

import h3lper.cli.combine_tiles
import h3lper.cli.raster_tiling
import h3lper.cli.vector_tiling


@click.group
def cli():  # noqa: D103
    pass


cli.add_command(h3lper.cli.combine_tiles.main)
cli.add_command(h3lper.cli.raster_tiling.main)
cli.add_command(h3lper.cli.vector_tiling.main)

if __name__ == "__main__":
    cli()
