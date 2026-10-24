# How to verify the SecureBank demo

Run these commands from `D:\HCL_Hackathon` in PowerShell.

## 1. Full automated checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports\pytest-results.xml
.\.venv\Scripts\python.exe -m evals.run_all_evals
```

Pytest checks API authentication and input validation, session and PIN security, agent routing, the Streamlit chat and PIN/confirmation UI, SQLite ownership and writes, RAG citations and abstention, FAISS persistence, and the supplied dataset adapter. The dataset integration test copies the SQLite file to a temporary directory and exercises all 14 registered banking tools through the gateway. Card blocking and dispute creation affect only that disposable test copy.

The evaluation command writes detailed JSON/CSV/HTML results and `reports/FINAL_EVALUATION_REPORT.md`. Routing and response checks use authored synthetic cases; RAG checks approved policy sources. These scores measure this prototype's deterministic baseline, not live LLM behavior or production safety.

## 2. Validate the supplied SQLite data

The source folder includes its own validator. Run it against the project's local copy:

```powershell
.\.venv\Scripts\python.exe D:\Downloads\securebank-ai\securebank-ai\database\validate_database.py --db runtime\data\securebank_demo.db
```

It should print `23/23 checks passed`. The app database is a local copy; the source dataset is not modified by tests.

## 3. Check the persistent FAISS index

```powershell
.\.venv\Scripts\python.exe -c "from app.rag.retrieval import Retriever; r=Retriever(); print(r.cache_dir, r.index.ntotal)"
Get-ChildItem runtime\faiss
```

Expect `runtime/faiss/policies.faiss`, `vectorizer.json`, and `manifest.json`; the index currently has 19 policy chunks. Starting a second `Retriever` should reuse the cache. If approved policy files or embedding settings change, it rebuilds the index. To force a clean rebuild, stop FastAPI and remove `runtime\faiss`.

## 4. Run the app and do a quick UI check

If a development PIN has not been set, run this once and choose a local test PIN:

```powershell
.\.venv\Scripts\python.exe scripts\set_demo_pin.py
```

Start the backend and UI in separate terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8501` and try:

1. `What is UPI?` — should answer with a policy citation without showing a PIN form.
2. `My balance` — should show the PIN form before any balance is returned.
3. Enter the local PIN — should show the selected customer's available balance.
4. `Show my cards`, then ask to block one exact active card ID — should require PIN and exact confirmation. This changes the local demo database; re-copy the source `.db` to reset it.

The automated Streamlit tests exercise the UI and auth forms with the mock fixtures; the dataset integration test exercises the actual dataset through the API and tool gateway. The real browser steps above confirm the running local processes are reachable.

## Last recorded results

Update this report after changing code by running the commands above. Evaluation artifacts are under `reports/`; the consolidated report is `reports/FINAL_EVALUATION_REPORT.md`. Tests use temporary credentials and disposable DB copies. The local `.env` must have a demo PIN hash before a person can complete protected requests in the running UI.
