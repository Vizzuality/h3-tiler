"""
Copy CSV into postgres table and build index structure for tiling fast 😎
"""

import os
from io import StringIO

import click
import h3
import pandas as pd
import psycopg
from psycopg import sql


def get_connection_info() -> str:
    """Returns a connection info string for psycopg based on env variables"""
    return psycopg.conninfo.make_conninfo(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USERNAME"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("table_name", type=click.STRING)
@click.option("--no-hex", is_flag=True, help="Don't convert h3index column to hex string.")
@click.option("--no-res-column", is_flag=True, help="Don't add resolution column.")
@click.option("--build_index", is_flag=True, help="Build index for tiling.")
def main(input_file: str, table_name: str, no_hex: bool, no_res_column: bool, build_index: bool):
    """Convert a csv file with h3index and value columns to a table in the database."""
    # Quick check that the connection is OK. Exception if not.
    with psycopg.connect(get_connection_info()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")

    click.echo("Reading csv file...")
    df = pd.read_csv(input_file)
    if not no_hex:
        click.echo("Converting h3index column to hex string...")
        # Convert to hex string, needed in h3-pg functions.
        # This is slow af but currently there's no way to format natively
        # in polars: https://github.com/pola-rs/polars/issues/7133
        df["h3index"] = df["h3index"].apply(lambda x: hex(x)[2:])
    if not no_res_column:
        click.echo("Adding res column...")
        df["res"] = df["h3index"].apply(lambda x: h3.get_resolution(x))

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

            with StringIO() as buffer:
                df.to_csv(buffer, na_rep="NULL", header=False, index=False)
                buffer.seek(0)

                with cur.copy(
                    sql.SQL("COPY {} FROM STDIN DELIMITER ',' CSV NULL 'NULL';").format(
                        sql.Identifier(table_name)
                    )
                ) as copy:
                    copy.write(buffer.read())

        if build_index:
            click.echo("Building indexes...")
            click.echo("Building index for res column...")
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE INDEX res_idx ON {} USING BRIN(res);").format(
                        sql.Identifier(table_name)
                    )
                )
                for res in range(5, 9):
                    click.echo(f"Building index for overview res {res}...")
                    parent_res = res - 5

                    cur.execute(
                        sql.SQL(
                            """
                        CREATE INDEX {}
                            on {} (h3_cell_to_parent(h3index, {}))
                            where res = {};
                        """
                        ).format(
                            sql.Identifier(f"{res}_to_{parent_res}_idx"),
                            sql.Identifier(table_name),
                            sql.Literal(parent_res),
                            sql.Literal(res),
                        )
                    )

                click.echo("Building index for overview res 6")

    click.echo("Done :)")


if __name__ == "__main__":
    main()
