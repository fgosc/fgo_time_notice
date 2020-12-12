.PHONY: deploy lock

deploy:
	chalice deploy

lock:
	pipenv lock -r > requirements.txt
