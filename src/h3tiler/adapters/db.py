"""
Database adapter for h3tiler

Here are the functions that talk to the db and return data given a h3index.
"""

import connectorx as cx
import h3
import psycopg
import pyarrow as pa
from psycopg import ClientCursor, connect, sql

from ..config import get_settings


def get_connection_info() -> str:
    """Returns a connection info string for psycopg based on env variables"""
    return psycopg.conninfo.make_conninfo(
        host=get_settings().POSTGRES_HOST,
        port=get_settings().POSTGRES_PORT,
        user=get_settings().POSTGRES_USERNAME,
        password=get_settings().POSTGRES_PASSWORD,
    )


def get_db_url() -> str:
    """Returns a db url for sqlalchemy based on env variables"""
    return (
        f"postgresql://{get_settings().POSTGRES_USERNAME}:{get_settings().POSTGRES_PASSWORD}"
        f"@{get_settings().POSTGRES_HOST}:{get_settings().POSTGRES_PORT}/{get_settings().POSTGRES_DB}"
    )


URL = get_db_url()


def get_tile_from_h3index(h3_tile_index: str, column: str, table: str) -> pa.Table:
    """Query and fetch the tile cells from the database"""
    h3_tile_res = h3.get_resolution(h3_tile_index)
    h3_res = min(h3_tile_res + 5, 8)
    raw_sql = sql.SQL(
        """
        select h3index::bigint, {col}
        from {table}
            where res = {h3_res} and h3_to_parent(h3index, {h3_tile_res}) = {h3_tile_index} and {col} is not null
        """
    ).format(
        h3_res=sql.Literal(h3_res),
        col=sql.Identifier(column),
        table=sql.Identifier(table),
        h3_tile_res=sql.Literal(h3_tile_res),
        h3_tile_index=sql.Literal(h3_tile_index),
    )

    with connect(URL, cursor_factory=ClientCursor) as con:
        query = con.cursor().mogrify(raw_sql)

    data = cx.read_sql(URL, query, return_type="arrow", protocol="binary")
    return data
