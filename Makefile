.PHONY: deploy lock

deploy:
	chalice deploy

lock:
	uv export --no-hashes --format requirements-txt --output-file requirements.txt
