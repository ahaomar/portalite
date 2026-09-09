import hashlib
import json
import pathlib
import threading
import datetime
import re

import duckdb
import pandas as pd

from .config import DATA_DIR, REGISTRY_PATH
from .geo import CENTROIDS, ISO2_TO_NAME
from .ingest import clean_columns, schema_from_df, detect_geo, attach_iso2


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:40] or "dataset"


class Store:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.con = self._connect()
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS portal_datasets (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                description VARCHAR,
                file VARCHAR,
                file_type VARCHAR,
                table_name VARCHAR,
                row_count BIGINT,
                schema_json VARCHAR,
                geo_json VARCHAR,
                uploaded_at VARCHAR
            )
        """)

    def _connect(self):
        try:
            con = duckdb.connect(str(DATA_DIR / ".portalite.duckdb"))
        except Exception as e:
            print(f"[portalite] database failed to open ({e}); quarantining and starting fresh")
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            for suffix in ("", ".wal"):
                f = pathlib.Path(str(DATA_DIR / ".portalite.duckdb") + suffix)
                if f.exists():
                    f.rename(f.with_name(f.name + f".broken-{stamp}"))
            con = duckdb.connect(str(DATA_DIR / ".portalite.duckdb"))
        try:
            con.execute("SET threads TO 1")
        except Exception:
            pass
        return con


    def _cursor(self):
        """Fresh connection object per operation — DuckDB connections are not thread-safe."""
        cur = self.con.cursor()
        try:
            cur.execute("SET threads TO 1")
        except Exception:
            pass
        return cur

    def _now(self):
        return datetime.datetime.utcnow().isoformat() + "Z"

    def list_datasets(self):
        with self._lock:
            cur = self._cursor()
            rows = cur.execute(
                "SELECT * FROM portal_datasets ORDER BY uploaded_at DESC"
            ).fetchall()
            cols = [d[0] for d in cur.description]
            out = []
            for r in rows:
                d = dict(zip(cols, r))
                d["schema"] = json.loads(d.pop("schema_json"))
                d["geo"] = json.loads(d.pop("geo_json")) if d["geo_json"] else None
                out.append(d)
            return out

    def get(self, dataset_id):
        with self._lock:
            cur = self._cursor()
            row = cur.execute(
                "SELECT * FROM portal_datasets WHERE id = ?", [dataset_id]
            ).fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            d = dict(zip(cols, row))
            d["schema"] = json.loads(d.pop("schema_json"))
            d["geo"] = json.loads(d.pop("geo_json")) if d["geo_json"] else None
            return d

    def _register(self, df: pd.DataFrame, name, description, file_name, file_type):
        with self._lock:
            df = clean_columns(df)
            geo = detect_geo(df, schema_from_df(df))
            df, geo = attach_iso2(df, geo)
            schema = schema_from_df(df)
            key = f"{name}-{file_name}"
            ds_id = f"{slugify(name)}-{hashlib.sha1(key.encode()).hexdigest()[:6]}"
            table = f"ds_{ds_id.replace('-', '_')}"
            cur = self._cursor()
            cur.register("ingest_view", df)
            cur.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM ingest_view')
            cur.unregister("ingest_view")
            cur.execute("DELETE FROM portal_datasets WHERE id = ?", [ds_id])
            cur.execute(
                "INSERT INTO portal_datasets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ds_id, name, description, file_name, file_type, table,
                    len(df), json.dumps(schema), json.dumps(geo) if geo else None,
                    self._now(),
                ],
            )
            return self.get(ds_id)

    def ingest_path(self, path: pathlib.Path, name=None, description=""):
        path = pathlib.Path(path)
        ext = path.suffix.lower()
        stem = path.stem
        if ext == ".csv":
            df = self._read_csv_robust(path)
        elif ext == ".json":
            df = pd.read_json(path)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            raise ValueError(f"unsupported file type: {ext}")
        return self._register(
            df, name or stem.replace("_", " ").replace("-", " ").title(),
            description, path.name, ext.lstrip("."),
        )

    def _read_csv_robust(self, path):
        try:
            df = pd.read_csv(path, sep=None, engine="python")
            if self._header_looks_valid(df):
                return self._maybe_unpivot(df)
        except Exception:
            pass
        import csv as _csv
        sample = path.read_text(encoding="utf-8", errors="replace")[:64 * 1024]
        try:
            dialect = _csv.Sniffer().sniff(sample, delimiters=",;\t|")
            delim = dialect.delimiter
        except Exception:
            delim = ","
        lines = []
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            for row in _csv.reader(fh, delimiter=delim):
                while row and not str(row[-1]).strip():
                    row.pop()
                if row:
                    lines.append(row)
        header_idx, header = self._find_header_row(lines)
        if header_idx is None:
            raise ValueError("could not detect a header row in this file")
        ncol = len(header)
        rows = []
        skipped = 0
        for row in lines[header_idx + 1:]:
            if not any(cell.strip() for cell in row):
                continue
            if len(row) == ncol:
                rows.append(row)
            elif len(row) < ncol:
                rows.append(row + [""] * (ncol - len(row)))
            else:
                skipped += 1
        named = [
            re.sub(r"[^\w]+", "_", (h or "")).strip("_").lower() or f"c{i}"
            for i, h in enumerate(header)
        ]
        df = pd.DataFrame(rows, columns=named)
        if skipped:
            print(f"[portalite] {path.name}: skipped {skipped} malformed rows")
        return self._maybe_unpivot(df)

    @staticmethod
    def _header_looks_valid(df):
        if df.shape[1] < 2:
            return False
        name_score = sum(1 for c in df.columns if re.match(r"^[a-z][a-z0-9_]*$", str(c)))
        return name_score / len(df.columns) >= 0.5

    @staticmethod
    def _find_header_row(lines, max_scan=25):
        scored = []
        for i, row in enumerate(lines[:max_scan]):
            non_empty = sum(1 for c in row if str(c).strip())
            if non_empty < 2:
                continue
            unique = len({str(c).strip() for c in row if str(c).strip()})
            scored.append((non_empty, unique, -i, i, row))
        if not scored:
            return None, None
        scored.sort(reverse=True)
        best = scored[0]
        if best[0] <= max((s[0] for s in scored[1:]), default=0) and len(scored) == 1:
            return best[3], best[4]
        return best[3], best[4]

    @staticmethod
    def _maybe_unpivot(df):
        """World Bank style wide tables: if many 4-digit-year columns, melt to long format."""
        year_cols = [c for c in df.columns if re.fullmatch(r"\d{4}", str(c).strip())]
        if len(year_cols) < 5 or len(year_cols) < len(df.columns) * 0.3:
            return df
        id_cols = [c for c in df.columns if c not in year_cols]
        if not id_cols:
            return df
        melted = df.melt(id_vars=id_cols, value_vars=year_cols, var_name="year", value_name="value")
        melted["year"] = pd.to_numeric(melted["year"], errors="coerce").astype("Int64")
        melted["value"] = pd.to_numeric(melted["value"], errors="coerce")
        melted = melted.dropna(subset=["value"])
        print(f"[portalite] wide-format detected ({len(year_cols)} year columns) — unpivoted to long format")
        return melted

    def ingest_upload(self, filename: str, content: bytes, name=None, description=""):
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        stem = pathlib.Path(safe).stem
        suffix = pathlib.Path(safe).suffix.lower()
        unique = f"{stem}-{hashlib.sha1(content).hexdigest()[:6]}{suffix}"
        dest = DATA_DIR / "uploads" / unique
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return self.ingest_path(dest, name or stem, description)

    def drop(self, dataset_id):
        with self._lock:
            meta = self.get(dataset_id)
            if not meta:
                return False
            cur = self._cursor()
            cur.execute(f'DROP TABLE IF EXISTS "{meta["table_name"]}"')
            cur.execute("DELETE FROM portal_datasets WHERE id = ?", [dataset_id])
            return True

    def rows(self, dataset_id, limit=50, offset=0, sort=None, direction="asc", q=None):
        with self._lock:
            meta = self.get(dataset_id)
            if not meta:
                return None
            limit = max(1, min(int(limit), 1000))
            offset = max(0, int(offset))
            cols = [c["name"] for c in meta["schema"]]
            where = ""
            params = []
            if q:
                like = f"%{q}%"
                conditions = " OR ".join(
                    [f'CAST("{c}" AS VARCHAR) ILIKE ?' for c in cols]
                )
                where = f"WHERE {conditions}"
                params = [like] * len(cols)
        order = ""
        if sort:
            if sort not in cols:
                raise ValueError(f"unknown sort column: {sort}")
            direction = "DESC" if str(direction).lower() == "desc" else "ASC"
            order = f'ORDER BY "{sort}" {direction} NULLS LAST'
        else:
            order = "ORDER BY rowid"
        sql = f'SELECT * FROM "{meta["table_name"]}" {where} {order} LIMIT {limit} OFFSET {offset}'
        out = self._cursor().execute(sql, params).df()
        return json.loads(out.to_json(orient="records"))

    def aggregate(self, dataset_id, group, value=None, agg="count", limit=12):
        with self._lock:
            meta = self.get(dataset_id)
            if not meta:
                return None
            cols = [c["name"] for c in meta["schema"]]
            if group not in cols:
                raise ValueError(f"unknown group column: {group}")
            if agg != "count" and value is None:
                raise ValueError("agg requires a value column")
            if value and value not in cols:
                raise ValueError(f"unknown value column: {value}")
            expr = "COUNT(*)" if agg == "count" else f'{agg}("{value}")'
            limit = max(1, min(int(limit), 100))
            sql = (
                f'SELECT "{group}" AS label, {expr} AS value '
                f'FROM "{meta["table_name"]}" WHERE "{group}" IS NOT NULL '
                f'GROUP BY 1 ORDER BY value DESC LIMIT {limit}'
            )
            out = self._cursor().execute(sql).df()
            return json.loads(out.to_json(orient="records"))

    def map_points(self, dataset_id, value=None, agg="count"):
        with self._lock:
            meta = self.get(dataset_id)
            if not meta:
                return None
            geo = meta["geo"]
            if not geo:
                return []
            cols = [c["name"] for c in meta["schema"]]
            if value and value not in cols:
                raise ValueError(f"unknown value column: {value}")
            table = meta["table_name"]
            if geo["kind"] == "latlon":
                sql = (
                    f'SELECT CAST("{geo["lat_col"]}" AS DOUBLE) AS lat, '
                    f'CAST("{geo["lon_col"]}" AS DOUBLE) AS lon '
                    f'FROM "{table}" '
                    f'WHERE "{geo["lat_col"]}" IS NOT NULL AND "{geo["lon_col"]}" IS NOT NULL LIMIT 500'
                )
                points = self._cursor().execute(sql).df().to_dict(orient="records")
                return [
                    {"lat": p["lat"], "lon": p["lon"], "value": 1, "label": ""}
                    for p in points
                ]
            iso_col = geo.get("iso2_col", "__iso2")
            expr = "COUNT(*)" if agg == "count" or not value else f'{agg}("{value}")'
            sql = (
                f'SELECT "{iso_col}" AS iso2, {expr} AS value FROM "{table}" '
                f'WHERE "{iso_col}" IS NOT NULL GROUP BY 1'
            )
            rows = self._cursor().execute(sql).df().to_dict(orient="records")
            points = []
            for r in rows:
                c = CENTROIDS.get(r["iso2"])
                if c:
                    points.append({
                        "iso2": r["iso2"],
                        "name": ISO2_TO_NAME.get(r["iso2"], r["iso2"]),
                        "lat": c[0], "lon": c[1], "value": r["value"],
                    })
            return points

    def stats(self):
        with self._lock:
            datasets = self.list_datasets()
            return {
                "datasets": len(datasets),
                "rows": sum(d["row_count"] for d in datasets),
                "columns": sum(len(d["schema"]) for d in datasets),
                "geospatial": sum(1 for d in datasets if d["geo"]),
            }


_store = None
_store_lock = threading.Lock()


def get_store() -> Store:
    global _store
    with _store_lock:
        if _store is None:
            _store = Store()
        return _store
