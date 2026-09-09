<div align="center">

# ◈ Portalite

**Turn any data file into a live, searchable data portal. In minutes. No coding. No servers to set up.**

Drop in a spreadsheet — get a website with search, charts, maps, and an API.

[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](#-installation)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](#-installation-with-docker-recommended)
[![Tests](https://img.shields.io/badge/tests-17%2F17-brightgreen)](#-testing)
[![License](https://img.shields.io/badge/license-MIT-blue)](#license)

</div>

---

## 🤔 What is this? (in plain words)

Imagine you have a spreadsheet — maybe your organization's budget, a list of schools, survey results, or pollution measurements.

You want to **share it on the web** so people can:

- 🔍 **search and browse** it like a website
- 📊 **see charts** of the important numbers
- 🗺️ **see a map** when the data mentions countries
- ⚙️ **let other apps read it** automatically

Usually that means hiring developers and setting up complicated servers.

**Portalite does it in one command.** You give it a data file. It gives you a complete, professional data website. That's it.

> **Think of it like this:** your spreadsheet goes in, a data website comes out. You don't need to install databases, configure servers, or write any code.

---
## ▶️ Demo Video ▶️▶

[![Demo](https://github.com/ahaomar/portalite/blob/main/demo.gif)](#Demo)
---

## 🚀 Installation

### ✅ With Docker (recommended — easiest way)

Docker runs Portalite in a self-contained "box" on your computer, so nothing conflicts with anything else you have installed.

#### Step 1 — Install Docker Desktop (one time only)

- **Windows / Mac**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop/) and install it. Open it once and wait until it says "running".
- **Linux**: Install [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/).

Check it works — open a terminal (Command Prompt / PowerShell on Windows, Terminal on Mac/Linux) and type:

```bash
docker --version
```

If you see a version number, you're ready.

#### Step 2 — Get Portalite

```bash
git clone https://github.com/ahaomar/portalite.git
cd portalite
```

> No `git`? Click the green **Code** button on this page → **Download ZIP** → unzip it, then open a terminal inside that folder.

#### Step 3 — Start it

```bash
docker compose up
```

First run takes a minute or two (it's building the box). When you see logs appear, it's ready.

#### Step 4 — Open your portal 🎉

Open your browser and go to:

**→ http://localhost:8080**

You'll see the catalog already containing two example datasets — click around! Charts, maps, search, everything works.

#### Step 5 — Stop it when you're done

Press `Ctrl + C` in the terminal. Your data is saved and will still be there next time you run `docker compose up`.

---

### 🐍 Without Docker (for those who prefer Python)

Requires Python 3.12 or newer from [python.org](https://www.python.org/downloads/).

```bash
git clone https://github.com/ahaomar/portalite.git
cd portalite

python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

pip install -r requirements.txt
PORTAL_DATA=./sample-data uvicorn app.main:app --port 8080
```

Open **http://localhost:8080** — same as above.

---

## 📊 Add your own data (the fun part)

### Option 1 — Drag and drop (easiest)

On the portal home page, simply **drag your file onto the upload box**. That's it.

- Supported: **CSV** (comma or semicolon separated), **Excel** (`.xlsx` and `.xls`), **JSON**
- Max size: 200MB

### Option 2 — Drop it in the folder

Put your file inside the `sample-data/` folder and restart (`Ctrl+C`, then `docker compose up` again). Every file in that folder automatically becomes a dataset.

### Option 3 — For developers: the API

```bash
curl -X POST http://localhost:8080/api/datasets -F "file=@mydata.csv" -F "name=My Data"
```

### What Portalite does with your file — automatically

| It figures out | What that gives you |
|---|---|
| What type each column is (text, number, date…) | Correct sorting and filtering |
| Where your data mentions countries or coordinates | A **map** with your data plotted on it |
| Which columns are interesting categories | **Charts** of the biggest values |
| Every word in every cell | **Search** across the whole dataset |
| The structure of your data | A **REST API** other apps can use |

**Works with tricky files too:** World Bank / UN exports with title rows above the data, semicolon-separated files, spreadsheets with one column per year — Portalite detects the real header and reshapes everything into clean, analyzable rows automatically.

---

## 🗺️ A real example

Import a World Bank poverty indicators file (the messy kind — metadata rows at the top, 66 year-columns across):

Portalite automatically:
1. Found the real header row (skipping the junk)
2. Converted 66 year-columns into 1,172 clean rows (`country, year, value`)
3. Detected country names → plotted **91 countries** on the map
4. Built search: `kenya` → 1992: 57.2%, 1994: 40.3%
5. Built the chart: highest poverty rates by country

You upload one file. You get all of this with zero clicks.

---

## 🔌 For developers: the automatic API

Every dataset instantly gets a documented REST API — full interactive docs at `/api/docs`.

```bash
# browse all datasets
curl http://localhost:8080/api/datasets

# rows with search, sort and pagination
curl "http://localhost:8080/api/datasets/{id}/rows?q=kenya&sort=year&direction=desc"

# aggregations
curl "http://localhost:8080/api/datasets/{id}/aggregate?group=country&value=value&agg=sum"

# map points
curl "http://localhost:8080/api/datasets/{id}/map"
```

Every dataset page in the UI links to its API endpoints — non-developers can copy API links to share data with technical partners.

---

## ⚙️ Configuration

| Setting | Default | What it does |
|---|---|---|
| `PORTAL_DATA` | `./sample-data` | The folder Portalite watches for data files |
| `PORTAL_PORT` | `8080` | Web port |

Where does my data live? Everything (uploaded files + the internal database) stays **on your machine** inside the data folder. Nothing is sent anywhere. Unplug the internet — everything still works.

---

## 🧪 Testing

The full test suite runs locally with no internet needed:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python test/run_tests.py
```

Expected result: `PASSED: 17  FAILED: 0` — covering ingestion, search, sorting, geo detection, maps, permissions, and concurrent access.

## 📁 Project structure

```
portalite/
├── app/               the engine
│   ├── main.py        web server + REST API
│   ├── store.py       data storage & queries (DuckDB)
│   ├── ingest.py      reads your files, finds the structure
│   ├── geo.py         country codes, names & map coordinates
│   └── config.py      settings
├── web/               the website (plain HTML/JS — no build step)
├── sample-data/       example datasets (your portal starts with these)
├── test/              automated tests
├── Dockerfile         the "box" recipe for Docker
└── docker-compose.yml one-command launcher
```

## 🛣️ Roadmap

- [ ] Shaded (choropleth) country maps
- [ ] Sheet picker for multi-sheet Excel files
- [ ] Dataset version history
- [ ] One-click static website export
- [ ] Scheduled auto-refresh of watched folders

## 🤝 Contributing

PRs welcome — the codebase is deliberately small (no frontend framework, no build step).

```bash
git clone https://github.com/ahaomar/portalite.git
cd portalite
python test/run_tests.py    # must stay green
```

## 📄 License

[MIT](LICENSE) © Muhammad Omar Farooq
