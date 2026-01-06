"""
Spectrum GSE — Minimal Smoke Test Suite

These tests confirm:
- The repo is structured correctly.
- Dependencies load.
- Basic files exist.
"""

import importlib
import pathlib


def test_readme_exists():
    """Ensure README.md exists at the project root."""
    root = pathlib.Path(__file__).resolve().parents[1]
    assert (root / "README.md").exists(), "README.md missing at project root."


def test_core_dependencies_import():
    """Ensure publicly declared dependencies import correctly."""
    deps = ["qiskit", "qiskit_aer", "numpy"]

    for dep in deps:
        try:
            importlib.import_module(dep)
        except Exception as e:
            raise AssertionError(f"Failed to import {dep}: {e}")
