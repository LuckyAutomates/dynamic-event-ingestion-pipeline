# Dynamic Event Ingestion Pipeline

Playwright scrapes quotes from Quotes to Scrape and sends them to a local
FastAPI endpoint. The API writes each batch to PostgreSQL's
`production_ingest` table.

## Requirements

- Python 3.10 or newer
- A local PostgreSQL server listening on `127.0.0.1:5432`
- A `production_ingest` table with `source_channel`, `payload_type`, and
  `structured_data` columns

Install the Python dependencies and Playwright browser:

```powershell
python -m pip install fastapi uvicorn psycopg2-binary playwright requests
python -m playwright install chromium
```

## Run locally

In PowerShell, set the PostgreSQL password for the current shell, then start
the API from this directory:

```powershell
$env:DB_PASSWORD = "your-postgres-password"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Leave the API running. In a second PowerShell window, from this directory,
run the scraper:

```powershell
python playwright_engine.py
```

The scraper opens Chromium, visits all quote pages, and posts the collected
`text` and `author` fields to `http://127.0.0.1:8000/ingest`. The API responds
with the number of inserted quotes. The password is read from `DB_PASSWORD`
by the API's database writer; do not commit credentials to this repository.
