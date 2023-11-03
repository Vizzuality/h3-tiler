"""Router for h3tiler."""

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .adapters.postgres import get_h3_tables, get_tile_from_h3index

h3index_router = APIRouter()


@h3index_router.get(
    "/{table}/{column}/{h3index}",
    responses={200: {"content": {"application/json": {}}, "description": "Return a tile"}},
    response_class=Response,
)
async def h3index(table: str, column: str, h3index: str, request: Request) -> Response:
    """Request a tile of h3 cells from a h3index"""
    async with request.app.async_pool.connection() as conn:
        data = await get_tile_from_h3index(h3index, column, table, conn)
    return Response(content=data, media_type="application/json")


@h3index_router.get(
    "/",
    responses={200: {"content": {"application/json": {}}, "description": "get list of tables"}},
    response_class=JSONResponse,
)
async def get_list_tables(request: Request) -> JSONResponse:
    """Request a tile of h3 cells from a h3index"""
    async with request.app.async_pool.connection() as conn:
        data = await get_h3_tables(conn)
    return JSONResponse(data, media_type="application/json")
