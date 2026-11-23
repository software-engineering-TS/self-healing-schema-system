# Changelog

## 2.1.1

- Updated Streamlit layout parameters to the current `width` API to remove deprecation warnings.

## 2.1.0

- Preserved the four-stage exact, normalized, fuzzy and optional AI matching workflow.
- Prevented normalized-name collisions from silently overwriting expected columns.
- Replaced per-source greedy fuzzy selection with maximum-weight one-to-one assignment.
- Added fuzzy ambiguity checks and strict validation for injected AI results.
- Validated Ollama response shape, mapping scope, finite confidence values and one-to-one constraints.
- Skipped semantic generation when the default Ollama service is unavailable.
- Expanded schema validation and made unmapped-column exclusion explicit.
- Added safe CSV header validation, upload size limits and generated upload filenames.
- Added automated tests, architecture/testing/limitations documentation and environment configuration examples.
- Removed the 85 MB local demo video from the source repository; retained the UI screenshots.