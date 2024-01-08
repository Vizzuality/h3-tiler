"""Router for h3tiler."""
import os

import h3
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from starlette.requests import Request
from starlette.responses import JSONResponse

from .adapters.postgres import (
    get_h3_table_columns,
    get_h3_tables_meta,
    get_tile_from_h3index,
)

h3index_router = APIRouter()


@h3index_router.get(
    "/tile/{h3index}",
    responses={200: {"description": "Return a tile"}, 404: {"description": "Not found"}},
    response_model=None,
)
async def h3index_parquet(h3index: str) -> FileResponse:
    """Request a tile of h3 cells from a h3index

    :raises HTTPException 404: Item not found
    """
    z = h3.get_resolution(h3index)
    file = f"/home/biel/Vizzuality/experiments/h3-tiler/data/test_arrow/{z}/{h3index}.arrow"
    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail="Item not found")
    return FileResponse(file, media_type="application/octet-stream")


@h3index_router.get(
    "/{table}/{column}/{h3index}",
    responses={200: {"content": {"application/json": {}}, "description": "Return a tile"}},
)
async def h3index(table: str, column: str, h3index: str, request: Request) -> Response:
    """Request a tile of h3 cells from a h3index"""
    async with request.app.async_pool.connection() as conn:
        data = await get_tile_from_h3index(h3index, column, table, conn)
    return Response(content=data, media_type="application/json")


@h3index_router.get(
    "/meta",
    responses={200: {"content": {"application/json": {}}, "description": "get list of tables"}},
)
async def get_list_tables(request: Request) -> JSONResponse:
    """Request a tile of h3 cells from a h3index"""
    async with request.app.async_pool.connection() as conn:
        data = await get_h3_tables_meta(conn)
    return JSONResponse(data, media_type="application/json")


@h3index_router.get(
    "/{table}",
    responses={200: {"content": {"application/json": {}}, "description": "get list of tables"}},
)
async def get_tables_columns(table: str, request: Request) -> JSONResponse:
    """Request a tile of h3 cells from a h3index"""
    async with request.app.async_pool.connection() as conn:
        data = await get_h3_table_columns(table, conn)
    return JSONResponse(data, media_type="application/json")
