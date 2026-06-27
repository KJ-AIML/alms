import sys
from pathlib import Path

# Add CLI source to path so alms_cli is importable
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
