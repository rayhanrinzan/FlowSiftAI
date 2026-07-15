"""Refresh a small set of leaf modules after Streamlit hot deployments."""

from __future__ import annotations

import builtins
import importlib
import sys
import threading


RUNTIME_VERSION = 13


def ensure_runtime_current() -> None:
    """Refresh changed service modules once without disrupting package imports."""

    lock = getattr(builtins, "_flowsift_runtime_lock", None)
    if lock is None:
        lock = threading.RLock()
        setattr(builtins, "_flowsift_runtime_lock", lock)

    with lock:
        active_version = int(getattr(builtins, "_flowsift_runtime_version", 0))
        if active_version >= RUNTIME_VERSION:
            return
        module_names = (
            "src.extraction.competitor_extractor",
            "src.services.opportunity_brief_service",
            "src.research.competitor_classifier",
            "src.research.query_generator",
            "src.services.research_service",
            "src.services.opportunity_service",
            "src.services.problem_scout_service",
            "src.ui.data",
        )
        refresh_complete = True
        for module_name in module_names:
            try:
                module = sys.modules.get(module_name)
                if module is None:
                    module = importlib.import_module(module_name)
                else:
                    module = importlib.reload(module)
                if module_name == "src.ui.data":
                    module.clear_ui_data_caches()
            except (ImportError, KeyError):
                # A clean process restart remains authoritative if a file watcher
                # invalidates a package during this best-effort refresh.
                refresh_complete = False
        if refresh_complete:
            setattr(builtins, "_flowsift_runtime_version", RUNTIME_VERSION)
