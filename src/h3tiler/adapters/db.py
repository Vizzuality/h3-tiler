import h3
import psycopg
from psycopg import sql

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
        where parent = any({tile_indexes}) and agg_value > 0
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


def paint_h3(h3indexes, h3res):
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


def get_tile_from_h3index(h3_tile_index: str, column, table) -> list[dict[str, float]]:
    h3_tile_res = h3.get_resolution(h3_tile_index)
    # FIXME for now, we get hardcode levels of resolution under the demanded tile. Should be more sensible
    h3_res = min(h3_tile_res + 5, 6)

    query = sql.SQL(
        """
        select h3_to_parent(h3index, {h3_res}) h3parent, avg({col}) value
        from {table}
            where h3_to_parent(h3index, {h3_tile_res}) = {h3_tile_index} and {col} > 0
        group by h3parent;
        """
    ).format(
        h3_res=sql.Literal(h3_res),
        col=sql.Identifier(column),
        table=sql.Identifier(table),
        h3_tile_res=sql.Literal(h3_tile_res),
        h3_tile_index=sql.Literal(h3_tile_index),
    )
    # TODO: improve talking with the db -> session should reuse connection?
    with psycopg.connect(get_connection_info()) as conn:
        with conn.cursor() as cur:
            # print(psycopg.ClientCursor(conn).mogrify(query))
            cur.execute(query)

            h3index_to_value = [
                {"h3index": h3index, "value": value} for h3index, value in cur.fetchall()
            ]
    return h3index_to_value
