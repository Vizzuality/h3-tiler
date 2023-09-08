"""Router for h3tiler."""

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..adapters.db import get_tile_from_h3index

h3index_router = APIRouter()


@h3index_router.get(
    "/h3index/{h3index}",
    responses={200: {"content": {"application/json": {}}, "description": "Return a tile"}},
    response_class=JSONResponse,
)
async def h3index(h3index: str, request: Request) -> JSONResponse:
    """Request a tile of h3 cells from a h3index"""
    async with request.app.async_pool.connection() as conn:
        data = await get_tile_from_h3index(h3index, "value", "h3_grid_deforestation_8", conn)
    json_data = jsonable_encoder(data)
    return JSONResponse(content=json_data)
