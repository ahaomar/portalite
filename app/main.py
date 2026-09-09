import pathlib

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .store import get_store
from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, DATA_DIR

app = FastAPI(title="Portalite", docs_url="/api/docs", redoc_url=None)


@app.middleware("http")
async def no_cache_api(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api") or request.url.path == "/health":
        response.headers["cache-control"] = "no-store, max-age=0"
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"internal error: {exc}"})


@app.on_event("startup")
def rescan_data_dir():
    """Ingest any supported file in the data dir that is not yet registered."""
    store = get_store()
    known = {d["file"] for d in store.list_datasets()}
    for path in sorted(DATA_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        if path.name.startswith("."):
            continue
        if path.name in known:
            continue
        try:
            meta = store.ingest_path(path)
            print(f"[portalite] ingested {path.name} -> {meta['name']} ({meta['row_count']} rows)")
        except Exception as e:
            print(f"[portalite] failed to ingest {path.name}: {e}")


@app.get("/health")
def health():
    return {"ok": True, "service": "portalite"}


@app.get("/api/stats")
def stats():
    return get_store().stats()


@app.get("/api/datasets")
def datasets():
    return get_store().list_datasets()


@app.get("/api/datasets/{dataset_id}")
def dataset_detail(dataset_id: str):
    meta = get_store().get(dataset_id)
    if not meta:
        raise HTTPException(404, "dataset not found")
    return meta


@app.get("/api/datasets/{dataset_id}/rows")
def dataset_rows(
    dataset_id: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: str = None,
    direction: str = Query("asc", pattern="^(asc|desc)$"),
    q: str = None,
):
    try:
        rows = get_store().rows(dataset_id, limit, offset, sort, direction, q)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if rows is None:
        raise HTTPException(404, "dataset not found")
    return {"rows": rows, "limit": limit, "offset": offset}


@app.get("/api/datasets/{dataset_id}/aggregate")
def dataset_aggregate(
    dataset_id: str,
    group: str,
    value: str = None,
    agg: str = Query("count", pattern="^(count|sum|avg|min|max)$"),
    limit: int = Query(12, ge=1, le=100),
):
    try:
        return get_store().aggregate(dataset_id, group, value, agg, limit)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/datasets/{dataset_id}/map")
def dataset_map(dataset_id: str, value: str = None, agg: str = Query("count", pattern="^(count|sum|avg|min|max)$")):
    try:
        return get_store().map_points(dataset_id, value, agg)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/datasets")
async def upload(
    file: UploadFile = File(...),
    name: str = Form(None),
    description: str = Form(""),
):
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"unsupported type {ext}. allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large (max 200MB)")
    try:
        meta = get_store().ingest_upload(file.filename, content, name, description)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(422, f"could not parse file: {e}")
    return meta


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str):
    if not get_store().drop(dataset_id):
        raise HTTPException(404, "dataset not found")
    return {"ok": True}


web_dir = pathlib.Path(__file__).parent.parent / "web"
app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/")
def index():
    return FileResponse(web_dir / "index.html")


@app.get("/dataset/{dataset_id}")
def dataset_page(dataset_id: str):
    return FileResponse(web_dir / "index.html")
