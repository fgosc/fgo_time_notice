.PHONY: deploy lock

deploy:
	chalice deploy --no-autogen-policy $(EXTRA_ARGS)

lock:
	uv export --no-hashes --format requirements-txt --output-file requirements.txt
