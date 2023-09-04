from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from starlette.middleware.cors import CORSMiddleware

from .adapters.db import get_connection_info
from .routers.router import h3index_router


@asynccontextmanager
async def lifespan(app_: FastAPI):
    app_.async_pool = AsyncConnectionPool(conninfo=get_connection_info())
    yield
    await app_.async_pool.close()


app = FastAPI(name="H3-Tiler", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(xyz_router)
app.include_router(h3index_router)
