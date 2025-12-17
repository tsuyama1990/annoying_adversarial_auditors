import sys
from pathlib import Path

# Add root directory to path to make ac_cdd_config importable
sys.path.append(str(Path(__file__).parents[2]))

try:
    from ac_cdd_config import config as _root_config
    # Re-export config
    config = _root_config
    settings = _root_config
except ImportError as e:
    # Fallback or error if config is missing (should not happen in normal flow)
    raise ImportError(
        "Could not import ac_cdd_config. Please ensure ac_cdd_config.py exists in the project root."
    ) from e
