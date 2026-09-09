#!/usr/bin/env python3
"""Portalite self-contained test suite — no external test framework needed."""
import io
import json
import os
import shutil
import sys
import tempfile
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

os.environ["PORTAL_DATA"] = tempfile.mkdtemp(prefix="portalite-test-")
DATA_DIR = pathlib.Path(os.environ["PORTAL_DATA"])

from fastapi.testclient import TestClient
from app.main import app

PASSED = []
FAILED = []


def test(name):
    def deco(fn):
        try:
            fn()
            PASSED.append(name)
            print(f"  ok - {name}")
        except AssertionError as e:
            FAILED.append(name)
            print(f"  FAIL - {name}: {e}")
        except Exception as e:
            FAILED.append(name)
            print(f"  ERROR - {name}: {type(e).__name__}: {e}")
        return fn
    return deco


client = TestClient(app)

# simulate a real data dir: copy samples in before startup scan runs
REPO_ROOT = pathlib.Path(__file__).parent.parent
for f in (REPO_ROOT / "sample-data").glob("*"):
    if f.is_file() and f.suffix.lower() in {".csv", ".json", ".xlsx", ".xls"}:
        shutil.copy(f, DATA_DIR / f.name)

with TestClient(app) as client:
    SAMPLE = DATA_DIR


@test("health endpoint")
def _():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


@test("sample data auto-ingested on startup")
def _():
    r = client.get("/api/datasets")
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert any("Displacement" in n for n in names), names
    assert any("Air" in n for n in names), names


@test("dataset detail includes schema and geo detection")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Displacement" in d["name"]][0]
    detail = client.get(f"/api/datasets/{ds['id']}").json()
    cols = [c["name"] for c in detail["schema"]]
    assert "country" in cols and "asylum_seekers" in cols
    assert detail["geo"] is not None, "country column should be detected as geo"
    assert detail["geo"]["kind"] == "country"
    assert detail["row_count"] == 15


@test("rows endpoint with limit and offset")
def _():
    r = client.get("/api/datasets")
    ds = r.json()[0]
    rows = client.get(f"/api/datasets/{ds['id']}/rows?limit=5").json()["rows"]
    assert len(rows) == 5
    rows2 = client.get(f"/api/datasets/{ds['id']}/rows?limit=5&offset=5").json()["rows"]
    assert rows2[0] != rows[0]


@test("rows sort desc on numeric column")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Displacement" in d["name"]][0]
    rows = client.get(f"/api/datasets/{ds['id']}/rows?limit=3&sort=asylum_seekers&direction=desc").json()["rows"]
    vals = [row["asylum_seekers"] for row in rows]
    assert vals == sorted(vals, reverse=True), vals
    assert vals[0] == 172000


@test("rows text search across all columns")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Displacement" in d["name"]][0]
    rows = client.get(f"/api/datasets/{ds['id']}/rows?q=syria").json()["rows"]
    assert len(rows) >= 1
    assert rows[0]["country"] == "Syria"


@test("rows rejects unknown sort column (injection guard)")
def _():
    r = client.get("/api/datasets")
    ds = r.json()[0]
    res = client.get(f"/api/datasets/{ds['id']}/rows?sort=1; DROP TABLE users")
    assert res.status_code == 400


@test("aggregate count by group")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Displacement" in d["name"]][0]
    agg = client.get(f"/api/datasets/{ds['id']}/aggregate?group=country&limit=15").json()
    assert len(agg) == 15
    values = [a["value"] for a in agg]
    assert values == sorted(values, reverse=True)


@test("aggregate sum with value column")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Displacement" in d["name"]][0]
    agg = client.get(f"/api/datasets/{ds['id']}/aggregate?group=country&value=asylum_seekers&agg=sum&limit=3").json()
    assert agg[0]["label"] == "Syria"
    assert agg[0]["value"] == 172000


@test("aggregate rejects unknown column (injection guard)")
def _():
    r = client.get("/api/datasets")
    ds = r.json()[0]
    res = client.get(f"/api/datasets/{ds['id']}/aggregate?group=nope")
    assert res.status_code == 400


@test("map points resolved to coordinates")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Displacement" in d["name"]][0]
    points = client.get(f"/api/datasets/{ds['id']}/map").json()
    assert len(points) == 15
    p = [x for x in points if x["iso2"] == "SY"][0]
    assert 30 < p["lat"] < 40 and 30 < p["lon"] < 45
    assert p["name"] == "Syria"


@test("json dataset (air quality) ingested with numeric types")
def _():
    r = client.get("/api/datasets")
    ds = [d for d in r.json() if "Air" in d["name"]][0]
    assert ds["row_count"] == 12
    types = {c["name"]: c["type"] for c in ds["schema"]}
    assert types["pm25_ugm3"] == "number"
    assert types["station"] == "string"
    assert types["year"] == "integer"


@test("upload new CSV via API")
def _():
    csv = "city,country,population_m\nLagos,Nigeria,15.4\nCairo,Egypt,22.1\nKinshasa,DR Congo,16.3\n"
    res = client.post(
        "/api/datasets",
        files={"file": ("megacities.csv", io.BytesIO(csv.encode()), "text/csv")},
        data={"name": "Megacities", "description": "test upload"},
    )
    assert res.status_code == 200, res.text
    meta = res.json()
    assert meta["name"] == "Megacities"
    assert meta["row_count"] == 3
    detail = client.get(f"/api/datasets/{meta['id']}").json()
    types = {c["name"]: c["type"] for c in detail["schema"]}
    assert types["population_m"] == "number"
    # cleanup
    d = client.delete(f"/api/datasets/{meta['id']}")
    assert d.json()["ok"] is True
    assert client.get(f"/api/datasets/{meta['id']}").status_code == 404


@test("upload rejects unsupported file types")
def _():
    res = client.post(
        "/api/datasets",
        files={"file": ("virus.exe", io.BytesIO(b"bad"), "application/octet-stream")},
    )
    assert res.status_code == 400


@test("stats endpoint")
def _():
    s = client.get("/api/stats").json()
    assert s["datasets"] >= 2
    assert s["rows"] >= 20


@test("404 for unknown dataset")
def _():
    assert client.get("/api/datasets/nope/rows").status_code == 404


@test("concurrent uploads + reads do not crash (duckdb thread safety)")
def _():
    import threading
    import urllib.request
    import io as _io
    results = []

    def upload(i):
        csv = f"city,country,pop\nCityA{i},Kenya,{100 + i}\nCityB{i},Nepal,{200 + i}\n".encode()
        body = (
            '----X\r\nContent-Disposition: form-data; name="file"; filename="conc%d.csv"\r\n'
            'Content-Type: text/csv\r\n\r\n' % i
        ).encode() + csv + b"\r\n----X--\r\n"
        try:
            r = client.post("/api/datasets", files={"file": ("conc%d.csv" % i, _io.BytesIO(csv), "text/csv")})
            results.append(r.status_code)
        except Exception as e:
            results.append(("ERR", str(e)[:100]))

    def read():
        try:
            r = client.get("/api/datasets")
            r.json()
            results.append(r.status_code)
        except Exception as e:
            results.append(("ERR", str(e)[:100]))

    threads = [threading.Thread(target=upload, args=(i,)) for i in range(5)]
    threads += [threading.Thread(target=read) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ok = sum(1 for r in results if r == 200)
    assert ok == len(results), f"{len(results) - ok} concurrent requests failed: {results[:5]}"


print("\n" + "=" * 45)
print(f"PASSED: {len(PASSED)}  FAILED: {len(FAILED)}")
if FAILED:
    sys.exit(1)
shutil.rmtree(DATA_DIR, ignore_errors=True)
