"""
Q-Lock Attractor Engine — Minimal Smoke Test Suite

These tests do NOT touch the proprietary attractor internals.
They simply confirm:
- The repo is structured correctly.
- Dependencies load.
- Basic files exist.

This gives the project immediate scientific legitimacy and allows
CI/CD integration later without exposing private IP.
"""

import importlib
import pathlib


def test_readme_exists():
    """Ensure README.md exists at the project root."""
    root = pathlib.Path(__file__).resolve().parents[1]
    assert (root / "README.md").exists(), "README.md missing at project root."


def test_readme_mentions_archive_status():
    """Ensure the README communicates the archived status."""
    root = pathlib.Path(__file__).resolve().parents[1]
    content = (root / "README.md").read_text().lower()
    assert "archived" in content and "no longer maintained" in content


def test_core_dependencies_import():
    """Ensure publicly declared dependencies import correctly."""
    deps = ["qiskit", "qiskit_aer", "numpy"]

    for dep in deps:
        try:
            importlib.import_module(dep)
        except Exception as e:
            raise AssertionError(f"Failed to import {dep}: {e}")
