"""Boundary tests: what the tools refuse, and what never reaches the wire.

Two reasons this exists next to the self-checks rather than inside them:

- The self-checks assert with `assert`, which `python3 -O` strips. These do
  not — `unittest`'s assertions are ordinary calls, so a run under `-O` still
  proves something.
- Every byte here is built on the spot. No project file, no vendor bundle, no
  controller: the suite runs identically on a fresh clone, which is exactly
  where a boundary is most likely to have rotted unnoticed.

Run: `python3 -m unittest discover -s tests -t .` from the repository root,
or `make check`, which does it for you.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "tools"))
