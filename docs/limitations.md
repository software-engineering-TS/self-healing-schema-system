# Known limitations

- The fuzzy assignment relies on SciPy for maximum-weight matching; the code has a deterministic greedy fallback if SciPy is unavailable.
- Semantic quality depends on the local Ollama model and the supplied column names; AI suggestions are thresholded but still require domain review for high-impact datasets.
- Fuzzy matching is name-based and cannot infer business meaning reliably.
- Missing expected columns are created with missing values; the application does not infer or synthesize data values.
- Unmapped incoming columns are intentionally excluded from the expected-schema CSV and are listed in validation warnings.
- Duplicate column labels are rejected because a source-to-target dictionary cannot represent duplicate labels safely.
- The current output contract is schema alignment, not type coercion, unit conversion, row-level data validation or semantic data-quality validation.
- The app is designed for trusted local use. It does not implement user authentication, multi-tenant access control or production deployment hardening.