"""Router for h3tiler."""

import pyarrow as pa
import pyarrow.compute
from fastapi import APIRouter
from starlette.responses import Response

from ..adapters.db import get_tile_from_h3index

h3index_router = APIRouter()


@h3index_router.get(
    "/h3index/{h3index}",
    responses={200: {"content": {"application/json": {}}, "description": "Return a tile"}},
    response_class=Response,
)
def h3index(h3index: str) -> Response:
    """Request a tile of h3 cells from a h3index"""
    data = get_tile_from_h3index(h3index, "value", "h3_grid_deforestation_8")
    data = data.cast(pa.schema({"h3index": pa.string(), "value": pa.float32()}))
    sink = pa.BufferOutputStream()
    with pa.RecordBatchStreamWriter(sink, data.schema) as writer:
        writer.write_table(data)

    arrow_file = pa.BufferReader(sink.getvalue())
    return Response(content=arrow_file.read(), media_type="application/octet-stream")
