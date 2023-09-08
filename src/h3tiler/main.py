"""Main module for the H3-Tiler API."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request

from .adapters.db import get_connection_info
from .routers.router import h3index_router


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Share a connection pool across the app."""
    app_.async_pool = AsyncConnectionPool(conninfo=get_connection_info())
    yield
    await app_.async_pool.close()


app = FastAPI(name="H3-Tiler", lifespan=lifespan)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adds a Server-Timing header to the response."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["Server-Timing"] = f"app;dur={str(process_time)}"
    return response


app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(h3index_router)
