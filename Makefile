.PHONY: install init run test clean

install:
	pip install -r requirements.txt

init:
	python -m app.db.init_db

run:
	streamlit run app/main.py --server.port 8501

test:
	python -m pytest tests/ -v

clean:
	rm -f wallet_watch.db
	rm -rf __pycache__ app/**/__pycache__ tests/__pycache__
