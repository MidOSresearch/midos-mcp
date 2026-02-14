# Bootstrap: redirect imports to src/hive_commons/
# This file exists because the project directory shadows the installed package
# when CWD is the monorepo root (D:\Proyectos\1midos).
import importlib
import sys
from pathlib import Path

_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Re-import from the real package location
if "hive_commons" in sys.modules:
    del sys.modules["hive_commons"]
_real = importlib.import_module("hive_commons")
sys.modules[__name__] = _real
