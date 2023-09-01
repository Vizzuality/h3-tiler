import mercantile
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from h3ronpy.arrow import vector
from shapely.geometry import box
from starlette.responses import JSONResponse

from ..adapters.db import get_tile_from_h3index, paint_h3

xyz_router = APIRouter()
h3index_router = APIRouter()


@xyz_router.get(
    "/tile/{z}/{x}/{y}",
    responses={200: {"content": {"application/json": {}}, "description": "Return a tile"}},
    response_class=JSONResponse,
)
def zxy_tile(z: int, x: int, y: int) -> JSONResponse:
    # t0 = datetime.now()
    # with Profiler() as profiler:
    tile = mercantile.Tile(x=x, y=y, z=z)
    h3res = max(min(z, 6), 3)
    h3indexes = vector.geometry_to_cells(box(*mercantile.bounds(tile)), h3res).to_pylist()
    h3indexes = [hex(index)[2:] for index in h3indexes]

    h3index_to_value = paint_h3(h3indexes, h3res)

    json_data = jsonable_encoder(h3index_to_value)
    return JSONResponse(content=json_data)


@h3index_router.get(
    "/h3index/{h3index}",
    responses={200: {"content": {"application/json": {}}, "description": "Return a tile"}},
    response_class=JSONResponse,
)
def h3index(h3index: str) -> JSONResponse:
    data = get_tile_from_h3index(
        h3index, "deforestByHumanLu202010Km", "h3_grid_deforestation_global"
    )
    json_data = jsonable_encoder(data)
    return JSONResponse(content=json_data)
