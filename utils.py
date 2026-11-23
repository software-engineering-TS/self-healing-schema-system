"""Pure helper utilities shared by the schema healing project."""
import csv
import io
import json
import re
from collections import Counter
from typing import List, Optional

import pandas as pd


def normalize_column(col: str) -> str:
    """Normalize a column name while preserving Unicode letters and digits."""
    if col is None:
        return ""
    value = str(col).strip().casefold()
    value = re.sub(r"[_\-]+", " ", value)
    value = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_columns(columns) -> List[str]:
    return [normalize_column(column) for column in columns]


def read_expected_schema(schema_df: pd.DataFrame) -> List[str]:
    if schema_df is None or schema_df.empty or len(schema_df.columns) == 0:
        raise ValueError("Expected schema CSV must contain a header and at least one column name")
    raw = schema_df.iloc[:, 0].dropna().astype(str).str.strip().tolist()
    if raw and normalize_column(raw[0]) == "expected column name":
        raw = raw[1:]
    if not raw:
        raise ValueError("Expected schema contains no column names")
    if any(not name for name in raw):
        raise ValueError("Expected schema contains an empty column name")
    duplicates = [name for name, count in Counter(raw).items() if count > 1]
    if duplicates:
        raise ValueError(f"Expected schema contains duplicate column names: {duplicates}")
    return raw


def build_comparison_df(expected_cols: List[str], actual_cols: List[str]) -> pd.DataFrame:
    max_len = max(len(expected_cols), len(actual_cols))
    pad = lambda values: list(values) + [""] * (max_len - len(values))
    return pd.DataFrame({"Expected Columns": pad(expected_cols), "Incoming Columns": pad(actual_cols)})


def extract_json(text: str) -> Optional[dict]:
    """Extract a JSON object, including one wrapped in Markdown fences."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char == "{":
            try:
                value, _ = decoder.raw_decode(text[index:])
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                continue
    return None


def validate_csv_header(content: bytes, filename: str = "uploaded.csv") -> List[str]:
    """Validate the first CSV row before pandas can silently mangle duplicate headers."""
    if not content:
        raise ValueError(f"{filename} is empty")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{filename} must use UTF-8 encoding") from exc
    try:
        header = next(csv.reader(io.StringIO(text)))
    except (csv.Error, StopIteration) as exc:
        raise ValueError(f"{filename} does not contain a valid CSV header") from exc
    names = [name.strip() for name in header]
    if not names or any(not name for name in names):
        raise ValueError(f"{filename} contains an empty column name")
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    if duplicates:
        raise ValueError(f"{filename} contains duplicate column names: {duplicates}")
    return names