"""Central configuration for the AI Schema Healing System."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("SCHEMA_HEALER_DATA_DIR", str(BASE_DIR)))
LOG_DIR = DATA_DIR / "logs"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
for directory in (LOG_DIR, UPLOAD_DIR, REPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "schema_healing.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL = os.getenv("SCHEMA_HEALER_LOG_LEVEL", "INFO").upper()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GENERATE = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "3"))
OLLAMA_RETRY_DELAY = float(os.getenv("OLLAMA_RETRY_DELAY", "2"))

FUZZY_THRESHOLD = int(os.getenv("FUZZY_THRESHOLD", "75"))
AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.60"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))

APP_TITLE = "AI Schema Healing System"
APP_ICON = "🧠"
APP_VERSION = "2.1.1"