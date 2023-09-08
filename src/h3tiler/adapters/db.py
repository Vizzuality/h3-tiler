"""
Database adapter for h3tiler

Here are the functions that talk to the db and return data given a h3index.
"""

import h3
import psycopg
from psycopg import AsyncConnection, sql

from ..config import get_settings


def make_query_aggregate_first(
    h3res: int, column: str, table: str = "h3_grid_aqueduct_global"
) -> psycopg.sql.Composed:
    """Does the aggregation to desired h3res first then filters"""
    return sql.SQL(
        """
        select parent, agg_value
        from (
            select h3_to_parent(h3index, {h3res}) parent, avg({column}) agg_value
            from {table}
            group by parent
            ) as h3_grid
        where parent = any({tile_indexes}) and agg_value is not null;
        """
    ).format(
        h3res=sql.Literal(h3res),
        column=sql.Identifier(column),
        table=sql.Identifier(table),
        tile_indexes=sql.Placeholder(),
    )


def get_connection_info() -> str:
    """Returns a connection info string for psycopg based on env variables"""
    return psycopg.conninfo.make_conninfo(
        host=get_settings().POSTGRES_HOST,
        port=get_settings().POSTGRES_PORT,
        user=get_settings().POSTGRES_USERNAME,
        password=get_settings().POSTGRES_PASSWORD,
    )


def xyz_paint_h3(h3indexes, h3res):
    """DEPRECATED: we use h3index now instead of xyz"""
    with psycopg.connect(get_connection_info(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                make_query_aggregate_first(
                    h3res, "deforestByHumanLu202010Km", "h3_grid_deforestation_global"
                ),
                [h3indexes],
            )
            h3index_to_value = [
                {"h3index": h3index, "value": value} for h3index, value in cur.fetchall()
            ]
    return h3index_to_value


async def get_tile_from_h3index(
    h3_tile_index: str, column, table, connection: AsyncConnection
) -> list[dict[str, float]]:
    """Query and fetch the tile cells from the database"""
    h3_tile_res = h3.get_resolution(h3_tile_index)
    h3_res = min(h3_tile_res + 4, 8)

    query = sql.SQL(
        """
        select h3index, {col}
        from {table}
            where res = {h3_res} and h3_to_parent(h3index, {h3_tile_res}) = {h3_tile_index} and {col} is not null;
        """
    ).format(
        h3_res=sql.Literal(h3_res),
        col=sql.Identifier(column),
        table=sql.Identifier(table),
        h3_tile_res=sql.Literal(h3_tile_res),
        h3_tile_index=sql.Literal(h3_tile_index),
    )
    async with connection as conn:
        async with conn.cursor() as cur:
            # print(psycopg.ClientCursor(conn).mogrify(query))
            await cur.execute(query)
            results = await cur.fetchall()
            h3index_to_value = [{"h3index": h3index, "value": value} for h3index, value in results]
    return h3index_to_value
