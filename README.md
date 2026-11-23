# AI-Powered Self-Healing Schema System

This repository contains the cleaned v2.1.1 release of a local-first Python application for reconciling incoming CSV schemas with a canonical target schema. It combines exact, normalized, fuzzy and optional Ollama semantic matching; validates mappings; reconstructs the healed dataset; and provides CSV/JSON exports through a Streamlit UI.

## Features

- Four progressive matching stages: exact, normalized, fuzzy and optional local AI semantic matching.
- Collision-aware normalized matching and one-to-one mapping constraints.
- AI response scope and confidence validation.
- Structured validation for missing, duplicate, invalid and unmapped columns.
- Reconstruction in canonical target-column order.
- Streamlit UI with CSV previews and healed CSV, mapping JSON and validation JSON downloads.
- Deterministic matching works without Ollama; AI is optional.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`
- Optional: [Ollama](https://ollama.com/) and the configured model (default `phi3`)

## Setup

```bash
git clone https://github.com/Tarunsai143/self-healing-schema-system.git
cd self-healing-schema-system
python -m venv .venv
```

Windows PowerShell activation:
```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux activation:
```bash
source .venv/bin/activate
```

Install and test:
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

Run the app:
```bash
streamlit run app.py
```

Optional AI setup:
```bash
ollama pull phi3
ollama serve
```

## Input format

- Expected schema CSV: first column contains canonical column names, one per row (including the header row).
- Incoming data CSV: header row contains incoming column names; remaining rows contain records.

Sample files are included in the repository.

## Outputs and data handling

The healed CSV has the expected columns in the expected order. Missing expected columns are retained with missing values. Unmapped incoming columns are not included in the healed CSV; they are shown in the validation report, so review that report before using output downstream.

## Architecture and testing

See `docs/architecture.md`, `docs/testing.md` and `docs/limitations.md`. The local test run reported 26 passing tests on Windows. The test suite mocks AI calls for deterministic CI; live Ollama behavior and browser interaction should be tested separately.

## Screenshots

![Upload and preview](media/uploaded_files_summary.png)

![Matching strategy summary](media/matching_strategy_summary.png)

![Download options](media/download_button.png)

## License

No license has been added. Reuse and redistribution terms are therefore not yet explicitly granted.
