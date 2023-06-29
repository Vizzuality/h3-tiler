import os

import geopandas as gpd
import mercantile
import numpy as np
import psycopg
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from h3ronpy import vector
from psycopg import sql
from shapely.geometry import box
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse


def get_connection_info() -> str:
    """Returns a connection info string for psycopg based on env variables"""
    return psycopg.conninfo.make_conninfo(
        host=os.getenv("API_POSTGRES_HOST"),
        port=os.getenv("API_POSTGRES_PORT"),
        user=os.getenv("API_POSTGRES_USERNAME"),
        password=os.getenv("API_POSTGRES_PASSWORD"),
    )


app = FastAPI(name="H3-Tiler", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_query_filter_first(
    h3res: int, column: str, table: str = "h3_grid_spam2010v2r0_global_prod"
) -> psycopg.sql.Composed:
    """Filers at res 6 first and then does the aggregation"""
    return sql.SQL(
        """
        select h3_to_parent(h3index, {}) h3, avg({}) from {} 
        where h3index = any({})
        group by h3
        """
    ).format(
        sql.Literal(h3res),
        sql.Identifier(column),
        sql.Identifier(table),
        sql.Placeholder(),
    )


def make_query_aggregate_first(
    h3res: int, column: str, table: str = "h3_grid_deforestation_global"
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
        where parent = any({tile_indexes})
        """
    ).format(
        h3res=sql.Literal(h3res),
        column=sql.Identifier(column),
        table=sql.Identifier(table),
        tile_indexes=sql.Placeholder(),
    )


@app.get(
    "/{z}/{x}/{y}",
    responses={
        200: {"content": {"application/json": {}}, "description": "Return a tile"}
    },
    response_class=JSONResponse,
)
def tile(z: int, x: int, y: int):

    # Tile logic
    tile = mercantile.Tile(x=x, y=y, z=z)
    tile_poly = box(*mercantile.bounds(tile))
    h3res = min(z, 6)
    _, h3indexes = next(vector.geometries_to_h3_generator([tile_poly], np.array([0], dtype=np.uint64), h3res))
    h3indexes = [hex(index)[2:] for index in h3indexes]

    # DB
    with psycopg.connect(get_connection_info(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                make_query_aggregate_first(h3res, "hansenLoss2021"),
                # make_query_aggregate_first(h3res, "hansenLossBuffered2021"),
                [h3indexes],
            )
            h3index_to_value = [
                {"h3index": h3index, "value": value, "tile": {"x": x, "y": y, "z": z}}
                for h3index, value in cur.fetchall()
            ]

    json_data = jsonable_encoder(h3index_to_value)
    return JSONResponse(content=json_data)
