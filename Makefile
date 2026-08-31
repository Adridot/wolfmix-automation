# The gate: every hardware-free self-check, then a summary that names every
# abstention. The canonical list lives in tools/check.py, not here.
#
# Exit 0 = all passed. Exit 3 = green, but something verified nothing (a clone
# with no corpus). Exit 1 = something failed. Must run from the repository
# root, stdlib only.
.PHONY: check
check:
	python3 tools/check.py
