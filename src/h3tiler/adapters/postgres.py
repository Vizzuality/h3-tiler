"""
Postgres database adapter for h3tiler.

It assumes that h3 extension is installed in the database.
"""

import h3
import psycopg
from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row

from ..config import get_settings


def get_connection_info() -> str:
    """Returns a connection info string for psycopg based on env variables"""
    return psycopg.conninfo.make_conninfo(
        host=get_settings().POSTGRES_HOST,
        port=get_settings().POSTGRES_PORT,
        user=get_settings().POSTGRES_USERNAME,
        password=get_settings().POSTGRES_PASSWORD,
    )


async def get_tile_from_h3index(
    h3_tile_index: str, column, table, connection: AsyncConnection
) -> bytes:
    """Query and fetch the tile cells from the database"""
    h3_tile_res = h3.get_resolution(h3_tile_index)
    h3_res = h3_tile_res + 5

    query = sql.SQL(
        """
        select json_agg(json_build_object(h3index, {col}))
        from {table}
            where res={h3_res}
            and h3_cell_to_parent(h3index, {h3_tile_res}) = {h3_tile_index}
            and {col} is not null;
        """
    ).format(
        h3_res=sql.Literal(h3_res),
        col=sql.Identifier(column),
        table=sql.Identifier(table),
        h3_tile_res=sql.Literal(h3_tile_res),
        h3_tile_index=sql.Literal(h3_tile_index),
    )

    async with connection.cursor(binary=True) as cur:
        # print(psycopg.ClientCursor(conn).mogrify(query))
        await cur.execute(query)
        results = cur.pgresult.get_value(0, 0)
        if not results:
            results = b"[]"
    return results


async def get_h3_tables_meta(conn: AsyncConnection) -> list:
    """returns a list of tables that have h3 indexes"""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            select h3_table_name, max_res, min_res, max_value, min_value, description, unit, name, column_name
            from meta
            """
        )
        results = await cur.fetchall()
    return results


async def get_h3_table_columns(table: str, conn: AsyncConnection) -> list:
    """returns a list of tables that have h3 indexes"""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            select column_name
            from information_schema.columns
            where table_name = %s and column_name != 'h3index'
            """,
            (table,),
        )
        results = [r[0] for r in await cur.fetchall()]
    return results
