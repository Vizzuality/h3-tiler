"""
Copy CSV into postgres table and build index structure for tiling fast 😎
"""

import os
from io import BytesIO

import click
import h3ronpy.polars  # noqa: F401
import polars as pl
import psycopg
from psycopg import sql


def get_connection_info() -> str:
    """Returns a connection info string for psycopg based on env variables"""
    return psycopg.conninfo.make_conninfo(
        dbname=os.environ.get("POSTGRES_DB"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        user=os.getenv("POSTGRES_USERNAME"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("table_name", type=str)
@click.option("--no-hex", is_flag=True, help="Don't convert h3index column to hex string.")
@click.option("--no-res-column", is_flag=True, help="Don't add resolution column.")
@click.option("--build-index", is_flag=True, help="Build index for tiling.")
@click.option(
    "--index-range",
    type=(int, int),
    help="TOP (lower resolution) to BOTTOM (higher resolution) range for relative parent index.",
)
@click.option(
    "--parent-step",
    type=click.INT,
    default=5,
    help="Relative parent resolution step. Used to build index.",
)
def main(
    input_file: str,
    table_name: str,
    no_hex: bool,
    no_res_column: bool,
    build_index: bool,
    index_range: tuple[int, int],
    parent_step: int,
):
    """Convert a csv file with h3index and value columns to a table in the database."""
    # Quick check that the connection is OK. Exception if not.
    with psycopg.connect(get_connection_info()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")

    click.echo("Reading csv file...")
    df = pl.read_csv(input_file, new_columns=["h3index", "value"])
    if not no_hex:
        click.echo("Converting h3index column to hex string...")
        df = df.with_columns(
            pl.col("h3index").cast(pl.Utf8).h3.cells_parse().h3.cells_to_string().alias("h3index")
        )
    if not no_res_column:
        click.echo("Adding res column...")
        df = df.with_columns(pl.col("h3index").h3.cells_parse().h3.cells_resolution().alias("res"))

    with psycopg.connect(get_connection_info()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {};").format(sql.Identifier(table_name)),
            )

            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE {} (
                    h3index h3index,
                    value float,
                    res int
                    )
                """
                ).format(sql.Identifier(table_name))
            )

            click.echo("Copying data to database...")

            with BytesIO() as buffer:
                df.write_csv(buffer, has_header=False)
                buffer.seek(0)

                with cur.copy(
                    sql.SQL("COPY {} FROM STDIN DELIMITER ',' CSV NULL 'NULL';").format(
                        sql.Identifier(table_name)
                    )
                ) as copy:
                    copy.write(buffer.read())

    if build_index:
        with psycopg.connect(get_connection_info()) as conn:
            click.echo("Building indexes...")
            click.echo("Building index for res column...")
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE INDEX {} ON {} USING BRIN(res);").format(
                        sql.Identifier(f"{table_name}_res_idx"), sql.Identifier(table_name)
                    )
                )

                for res in range(index_range[0], index_range[1] + 1):
                    click.echo(f"Building index for overview res {res}...")
                    parent_res = res - parent_step

                    cur.execute(
                        sql.SQL(
                            """
                        CREATE INDEX {}
                            on {} (h3_cell_to_parent(h3index, {}))
                            where res = {};
                        """
                        ).format(
                            sql.Identifier(f"{table_name}_{res}to{parent_res}_idx"),
                            sql.Identifier(table_name),
                            sql.Literal(parent_res),
                            sql.Literal(res),
                        )
                    )

    click.echo("Done :)")


if __name__ == "__main__":
    main()
