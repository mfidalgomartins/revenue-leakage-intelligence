"""
Runtime utilities for consistent local execution.
"""
import os
from pathlib import Path


def configure_runtime(project_root):
    """
    Configure runtime folders and environment variables used by scripts.
    Ensures Matplotlib cache is writable in restricted environments.
    """
    root = Path(project_root)
    cache_dir = root / ".cache" / "matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)

    mpl_config = os.environ.get("MPLCONFIGDIR")
    if not mpl_config:
        os.environ["MPLCONFIGDIR"] = str(cache_dir)

