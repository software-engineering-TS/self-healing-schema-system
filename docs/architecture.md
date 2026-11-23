# Architecture

The application is a local-first Streamlit interface backed by a Python schema reconciliation pipeline.

## Processing flow

1. **Input validation** checks that the expected schema and incoming DataFrame have non-empty, unique column names.
2. **Exact matching** maps identical names.
3. **Normalized matching** maps unique names after case-folding and separator/punctuation normalization. Collisions are reported, not silently resolved.
4. **Fuzzy matching** scores remaining candidates with RapidFuzz and uses SciPy maximum-weight one-to-one assignment. Low-confidence and ambiguous candidates remain unmatched.
5. **Optional semantic matching** sends only unresolved names to a local Ollama model. The service health is checked before attempting generation. The response is checked for valid JSON, in-scope names, numeric finite confidence, threshold and one-to-one constraints.
6. **Validation** reports missing expected fields, duplicate or invalid mappings, and unmapped incoming columns.
7. **Reconstruction** returns exactly the expected columns in expected order. Missing expected fields are represented as pandas missing values. Unmapped incoming fields are reported and excluded from the expected-schema output.

## Main modules

- `app.py`: Streamlit interface, upload handling and downloads.
- `matcher.py`: matching data structures and four-stage matching engine.
- `schema_healer.py`: Ollama integration, orchestration and reconstruction.
- `validator.py`: mapping validation and structured report.
- `utils.py`: normalization, schema parsing, comparison and JSON extraction.
- `config.py`: environment-overridable settings and runtime directories.
- `logger.py`: console and rotating file logging.

## Design constraints

- Ollama is optional; deterministic stages run without it.
- Mapping is one-to-one: a source and target can each be used at most once.
- Ambiguous normalization collisions are not auto-mapped.
- The output contract remains the expected schema in its supplied order.
- Runtime uploads, logs and reports are local artifacts and should not be committed.