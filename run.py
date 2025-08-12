import sys
from pathlib import Path

# Make project root importable whether run as module or script
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

# Try both import paths depending on how it's executed
try:
  from app.main import app  # when running as script: python backend/run.py
except ModuleNotFoundError:
  from backend.app.main import app  # when running as module: python -m backend.run

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)


