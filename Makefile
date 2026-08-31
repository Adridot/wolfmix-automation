# Tous les self-checks. Doit tourner depuis la racine du dépôt, stdlib seule.
.PHONY: check
check:
	python3 tools/wpjlib.py
	python3 tools/wpj_wire.py
	python3 tools/wpj_codec.py
	python3 tools/wpj_inspect.py
	python3 tools/wpj_bc.py
	python3 tools/wpj_show.py
	python3 tools/wpj_generate.py
	python3 tools/wpj_api.py
	python3 tools/wpj_identities.py
	python3 tools/wpj_position.py
	python3 tools/wolfmix_transaction.py
	python3 tools/wpj_privacy.py
	python3 tools/gobo_run.py
	python3 -m unittest discover -s tests -t .
