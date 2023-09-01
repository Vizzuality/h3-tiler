from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .routers.router import h3index_router, xyz_router

app = FastAPI(name="H3-Tiler")

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(xyz_router)
app.include_router(h3index_router)
