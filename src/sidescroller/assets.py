"""Paths to assets bundled with the installed package (never relative to cwd)."""
from pathlib import Path
ASSET_ROOT = Path(__file__).resolve().parent / 'assets'


def asset_path(relative):
    return ASSET_ROOT / relative
