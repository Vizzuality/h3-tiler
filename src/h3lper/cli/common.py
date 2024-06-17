import polars as pl
from polars.type_aliases import PolarsDataType


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
