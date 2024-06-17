import click

import h3lper.cli.combine_tiles
import h3lper.cli.tiling

@click.group
def cli():
    pass

cli.add_command(h3lper.cli.combine_tiles.main)
cli.add_command(h3lper.cli.tiling.main)

if __name__ == "__main__":
    cli()
