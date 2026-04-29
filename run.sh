source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 5098 --log-level debug --reload
deactivate
