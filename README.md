# FNOL Processing Agent

A lightweight agent that extracts key fields from **First Notice of Loss (FNOL)** documents, identifies missing or inconsistent fields, validates dates, classifies claims, and routes them to the correct workflow with a short explanation.

## Features

- Upload **PDF** or **TXT** files, or **paste FNOL text** directly
- Regex-based field extraction from structured and real-world FNOL layouts
- Flexible date parsing (`03/12/2025`, `May 1 2026`, `may1 2026`, `2026-06-20`)
- Missing mandatory field detection
- Priority-based claim routing with reasoning
- React UI with extracted fields, date validation, and raw JSON output

## Architecture

```
FNOLReact/
├── backend/           # Python FastAPI API
│   ├── main.py        # HTTP endpoints, request handling
│   ├── extractor.py   # PDF/text extraction + field parsing
│   ├── date_utils.py  # Date parsing and validation
│   └── router.py      # Claim routing rules
├── frontend/          # React + Vite UI
└── sample-documents/  # Test FNOL files (TXT/PDF)
```

| Layer | Stack |
|-------|-------|
| Frontend | React 19, Vite 8 |
| Backend | Python 3, FastAPI, pdfplumber |
| Communication | REST JSON / multipart; Vite dev proxy → port 8000 |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0  --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (or the port Vite prints if 5173 is in use).

### Windows shortcuts

```bash
start-backend.bat
start-frontend.bat
```

> **Important:** Only one backend process should run on port 8000. If extraction looks wrong after code changes, stop all uvicorn instances and restart the backend so the latest `extractor.py` is loaded.

## Usage

1. Open the frontend in your browser.
2. Choose **Upload file** (PDF/TXT) or **Paste text**.
3. Click **Analyze FNOL**.
4. Review the recommended route, extracted fields, missing fields, and date validation.

During development, the Vite proxy forwards `/api/*` to the backend — no CORS setup needed locally.

## Fields Extracted

| Group | Fields |
|-------|--------|
| **Policy Information** | Policy Number, Policyholder Name, Effective Dates |
| **Incident Information** | Date, Time, Location, Description |
| **Involved Parties** | Claimant, Third Parties, Contact Details |
| **Asset Details** | Asset Type, Asset ID, Estimated Damage |
| **Other** | Claim Type, Attachments, Initial Estimate |

Supported label variants include:

- `Insured Name` / `Policyholder Name`
- `Date of Loss` / `Incident Date` (including ISO `YYYY-MM-DD`)
- `Location of Loss` / `Location`
- `Description` / `Description of Loss` (multi-line)
- `Claimant Name`, `Claimant Phone`, `Claimant Email`
- `Make` / `Model` / `Year` / `VIN` (vehicle block)
- `Police Report Filed` / `Police Report Number`

## Routing Rules

Rules are evaluated in priority order (first match wins):

| Priority | Condition | Route |
|----------|-----------|-------|
| 1 | Description contains `fraud`, `inconsistent`, or `staged` | **Investigation Flag** |
| 2 | Claim type includes `injury` | **Specialist Queue** |
| 3 | Any mandatory field is missing | **Manual Review** |
| 4 | Estimated damage < $25,000 (all fields present) | **Fast-track** |
| 5 | Estimated damage ≥ $25,000 | **Standard Processing** |
| 6 | Fallback (all fields present, no damage amount) | **Standard Processing** |

## API

### `GET /health`

Returns `{ "status": "ok" }`.

### `POST /api/process-fnol`

Accepts either:

**JSON** (pasted text):

```bash
curl -X POST http://127.0.0.1:8000/api/process-fnol \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Policy Number: POL-123\nDescription of Loss:\nRear-end collision.\"}"
```

**Multipart** (file upload):

```bash
curl -X POST http://127.0.0.1:8000/api/process-fnol \
  -F "file=@sample-documents/fnol_fast_track.txt"
```

### Response

```json
{
  "extractedFields": {
    "policyInformation": { "policyNumber": "...", "policyholderName": "...", "effectiveDates": "..." },
    "incidentInformation": { "date": "...", "time": "...", "location": "...", "description": "..." },
    "involvedParties": { "claimant": "...", "thirdParties": "...", "contactDetails": "..." },
    "assetDetails": { "assetType": "...", "assetId": "...", "estimatedDamage": "...", "estimatedDamageNumeric": 8500 },
    "other": { "claimType": "...", "attachments": "...", "initialEstimate": "...", "initialEstimateNumeric": 8500 }
  },
  "missingFields": [],
  "dateValidation": {
    "incidentDate": { "raw": "2026-06-20", "normalized": "2026-06-20", "valid": true, "error": null },
    "effectiveDates": { "raw": null, "valid": false, "error": "Date range not provided", "start": null, "end": null }
  },
  "invalidDates": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage ($8,500.00) is below $25,000; eligible for fast-track processing."
}
```

## Sample Documents

Test files in `sample-documents/`:

| File | Expected route | Notes |
|------|----------------|-------|
| `fnol_fast_track.txt` | Fast-track | Complete claim, damage < $25k |
| `fnol_missing_fields.txt` | Manual Review | Missing incident time and attachments |
| `fnol_text_dates.txt` | Fast-track | Text-style dates (`May 1 2026`, `may1 2024`) |
| `fnol_missing_fields.pdf` | Manual Review | PDF version of missing-fields sample |

Generate PDFs from TXT samples:

```bash
cd backend
pip install fpdf2
python generate_pdfs.py
```

## Project Structure (backend)

| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI app, CORS, file/JSON ingestion |
| `extractor.py` | PDF text extraction, regex field parsing, enrichment |
| `date_utils.py` | Flexible date parsing and validation |
| `router.py` | Routing logic and reasoning strings |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS errors | Use the Vite dev server (`npm run dev`); it proxies `/api` to the backend |
| `404 Not Found` on API | Ensure backend is running on port 8000 |
| Wrong/missing extractions after code changes | Restart uvicorn completely (stop all instances, start fresh) |
| Port 8000 already in use | Kill the existing process or use a different port |
| `[object Object]` error in UI | Backend returned a validation error array; check the Network tab for details |

**Verify the backend is up to date:** after restart, process a document and confirm `claimant` is a name (e.g. `Sarah Mitchell`), not `Name: Sarah Mitchell`. If the old format appears, the server is still running stale code.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `""` (empty) | Frontend API base URL. Leave empty in dev to use the Vite proxy. Set to `http://127.0.0.1:8000` for direct calls. |

## License

Private / educational use.
