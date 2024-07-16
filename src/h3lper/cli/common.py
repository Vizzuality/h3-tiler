from pathlib import Path
from typing import Any, TypeVar

import pandas as pd
import polars as pl
from h3ronpy.h3ronpyrs import DEFAULT_CELL_COLUMN_NAME
from h3ronpy.pandas import change_resolution
from polars.type_aliases import PolarsDataType
from rich.progress import Progress

RESOLUTION_TO_LEVEL_DIFF = 5
MIN_TILE_LEVEL = 0


def make_polars_schema(meta: dict) -> dict[str, PolarsDataType]:
    """build polars schema from meta files"""
    numpy_to_polars_dtype = {
        "int8": pl.Int8,
        "int16": pl.Int16,
        "int32": pl.Int32,
        "int64": pl.Int64,
        "uint8": pl.UInt8,
        "uint16": pl.UInt16,
        "uint32": pl.UInt32,
        "uint64": pl.UInt64,
        "float16": pl.Float32,  # Polars does not have Float16, so map to Float32
        "float32": pl.Float32,
        "float64": pl.Float64,
        "str": pl.Utf8,
        "bool": pl.Boolean,
        "datetime64": pl.Datetime,
        "timedelta64": pl.Duration,
        "object": pl.Object,  # Use pl.Object for generic objects, although not recommended
        "void": pl.Null,  # Map NumPy void type to Polars Null
    }
    return {d["var_name"]: numpy_to_polars_dtype[d["var_dtype"]] for d in meta}


DF = TypeVar("DF", pl.DataFrame, pd.DataFrame)


def partition_dataframe_by_tile(df: DF, tile_level: int) -> dict[Any, DF]:
    """Partition dataframe by tile. Returns groups belonging to a
    tile of the given level"""
    if isinstance(df, pl.DataFrame):
        df = df.with_columns(
            pl.col(DEFAULT_CELL_COLUMN_NAME).h3.change_resolution(tile_level).alias("tile_id")
            # type: ignore[attr-defined]
        ).unique(subset=[DEFAULT_CELL_COLUMN_NAME])
        partitions = df.partition_by(["tile_id"], as_dict=True, include_key=False)

    elif isinstance(df, pd.DataFrame):
        df["tile_id"] = change_resolution(df[DEFAULT_CELL_COLUMN_NAME], tile_level).drop_duplicates(
            subset=DEFAULT_CELL_COLUMN_NAME
        )
        partitions = dict(iter(df.groupby("tile_id")))  # type: ignore[arg-type]

    else:
        raise ValueError(f"dataframe type {type(df)} not supported")

    return partitions


def write_tiles(
    partition_dfs: dict[Any, pd.DataFrame] | dict[Any, pl.DataFrame],
    progress: Progress,
    seen_tiles: set[int],
    base_level_path: Path,
):
    """Writes tiles"""
    write_tiles_task = progress.add_task("[cyan]Writing tiles...")

    for tile_group, tile_df in progress.track(partition_dfs.items(), task_id=write_tiles_task):
        tile_id = tile_group[0]
        filename = base_level_path / (hex(tile_id)[2:] + ".parquet")
        progress.update(write_tiles_task)
        if tile_id in seen_tiles:
            pl.concat([pl.read_parquet(filename), tile_df]).unique(
                subset=[DEFAULT_CELL_COLUMN_NAME]
            ).write_parquet(filename)
        else:
            tile_df.write_parquet(filename)
        seen_tiles.add(tile_id)
    progress.update(write_tiles_task, visible=False)
