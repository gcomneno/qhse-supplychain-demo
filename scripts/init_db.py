from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so "import app.*" works when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine
from app.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("OK: tables created (if models are defined).")
