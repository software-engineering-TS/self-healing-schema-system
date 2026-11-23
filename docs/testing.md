# Testing

Install dependencies and development tools:

```bash
python -m pip install -r requirements.txt
```

Run the suite from the repository root:

```bash
python -m pytest -q
```

The tests cover normalization, exact and normalized matching, normalization collisions, fuzzy one-to-one assignment, AI response validation and fallback, schema reconstruction, duplicate headers, JSON extraction and validator reports.

The sample regression test deliberately disables Ollama. It expects 2 normalized matches, 8 fuzzy matches and 2 unresolved expected fields (`person_id`, `diagnosis`) because the sample uses `id` and `diag` for those fields. These two semantic mappings require a functioning local Ollama model or an explicit domain mapping; deterministic code must not invent them.

The test suite does not replace a manual Streamlit browser test or a live Ollama integration test. Record those separately when executed in an environment with Streamlit and Ollama available.