import re
import json
import pandas as pd

from .config import COUNTRY_NAMES, LAT_COLS, LON_COLS
from .geo import COUNTRY_TO_ISO2, ISO3_TO_ISO2, CENTROIDS

FRIENDLY_TYPES = {
    "int64": "integer",
    "int32": "integer",
    "Int64": "integer",
    "float64": "number",
    "float32": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "datetime64[ns]": "date",
    "object": "string",
    "string": "string",
}


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen = {}
    new_cols = []
    for col in df.columns:
        name = re.sub(r"[^\w]+", "_", str(col)).strip("_").lower() or "col"
        if name[0].isdigit():
            name = f"c_{name}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        new_cols.append(name)
    df.columns = new_cols
    return df


def schema_from_df(df: pd.DataFrame):
    return [
        {"name": str(col), "type": FRIENDLY_TYPES.get(str(df[col].dtype), "string")}
        for col in df.columns
    ]


def is_numeric_type(t: str) -> bool:
    return t in ("integer", "number")


def detect_geo(df: pd.DataFrame, schema):
    string_cols = [c["name"] for c in schema if c["type"] == "string"]
    numeric_cols = [c["name"] for c in schema if is_numeric_type(c["type"])]

    lat_col = next((c for c in numeric_cols if c.lower() in LAT_COLS), None)
    lon_col = next((c for c in numeric_cols if c.lower() in LON_COLS), None)
    if lat_col and lon_col:
        return {"kind": "latlon", "lat_col": lat_col, "lon_col": lon_col}

    for col in string_cols:
        values = df[col].dropna().astype(str).head(200)
        if len(values) == 0:
            continue
        hits_iso2 = sum(1 for v in values if re.fullmatch(r"[A-Za-z]{2}", v) and v.upper() in CENTROIDS)
        hits_name = sum(1 for v in values if v.strip().lower() in COUNTRY_NAMES)
        hits_iso3 = sum(1 for v in values if re.fullmatch(r"[A-Za-z]{3}", v) and v.upper() in ISO3_TO_ISO2)
        n = len(values)
        if hits_iso2 / n >= 0.6:
            return {"kind": "country", "col": col, "source": "iso2"}
        if hits_name / n >= 0.6:
            return {"kind": "country", "col": col, "source": "name"}
        if hits_iso3 / n >= 0.6:
            return {"kind": "country", "col": col, "source": "iso3"}
    return None


def attach_iso2(df: pd.DataFrame, geo):
    if not geo or geo["kind"] != "country":
        return df, geo
    col = geo["col"]
    source = geo["source"]
    df = df.copy()

    def to_iso2(v):
        if pd.isna(v):
            return None
        v = str(v).strip()
        if source == "iso2":
            return v.upper() if v.upper() in CENTROIDS else None
        if source == "iso3":
            return ISO3_TO_ISO2.get(v.upper())
        return COUNTRY_TO_ISO2.get(v.strip().lower())

    df = df.copy()
    df["__iso2"] = df[col].map(to_iso2)
    geo = dict(geo)
    geo["iso2_col"] = "__iso2"
    return df, geo


def pick_chart_column(df: pd.DataFrame, schema, geo):
    categorical = [
        c["name"]
        for c in schema
        if c["type"] == "string" and df[c["name"]].nunique() <= 50
    ]
    if geo and geo["kind"] == "country" and geo["col"] in categorical:
        categorical.remove(geo["col"])
    return categorical[0] if categorical else None
