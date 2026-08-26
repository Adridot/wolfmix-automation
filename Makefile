# Tous les self-checks. Doit tourner depuis la racine du dépôt, stdlib seule.
.PHONY: check
check:
	python3 tools/wpjlib.py
	python3 tools/wpj_codec.py
	python3 tools/wpj_inspect.py
	python3 tools/wpj_show.py
	python3 tools/wpj_api.py
	python3 tools/wpj_identities.py
	python3 tools/wpj_position.py
