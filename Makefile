.PHONY: deploy lock

deploy:
	chalice deploy --no-autogen-policy

lock:
	pipenv lock -r > requirements.txt
