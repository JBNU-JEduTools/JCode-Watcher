import os
import sys
from pathlib import Path

os.environ.setdefault("DB_URL", "sqlite://")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
