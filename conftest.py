"""
Root conftest.py — adds the project root to sys.path so that top-level
packages (models, game, api, camera, database) are importable by pytest
without requiring an installed package or a src/ layout.
"""
import sys
import os

# Insert the project root at the front of sys.path once, at collection time.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
