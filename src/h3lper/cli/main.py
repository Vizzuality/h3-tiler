import click

import h3lper.cli.combine_tiles
import h3lper.cli.tiling

cli = click.CommandCollection(sources=[h3lper.cli.tiling.cli, h3lper.cli.combine_tiles.cli])

if __name__ == "__main__":
    cli()
