# Supplied dataset setup

The source dataset is `D:\Downloads\securebank-ai\securebank-ai`. Its SQLite database is `database\securebank_demo.db`; the `datasets` folder contains exports, while `database\schema.sql` and `database\data_dictionary.md` describe the schema. All customer records are synthetic demo data.

## Where the app reads it

Keep the working copy at `D:\HCL_Hackathon\runtime\data\securebank_demo.db`. This folder is ignored by Git, so the database will not be committed. The current local copy was copied from the source folder; re-copy that file there if you need to reset local card/dispute demo mutations.

The `.env` setting is:

```dotenv
REPOSITORY=securebank_dataset
DATABASE_PATH=runtime/data/securebank_demo.db
```

The application selects this adapter at startup. It reads the actual schema directly; there is no CSV import step. Do not upload the bank database to a public website or Git repository. For this hackathon prototype, the database is local and contains synthetic data.

## Start it

From D:\HCL_Hackathon, set the two .env database settings above, then run the account PIN setup command in README. The script prompts for a unique 4–12 digit PIN for each account, hides typed input, and stores only a salted Argon2id hash in account_security. You can provision one account with --account-id ACCOUNT_ID and rerun the all-accounts command to finish missing hashes. Restart FastAPI after setup. The sidebar loads customer IDs from the database; this fixture has one account per customer, so the selected customer PIN maps to that account.

The dataset stores salted login password hashes in `users.password_hash`. Those are not PIN hashes, so the prototype does not use them for PIN verification. Account PIN hashes are stored separately in `account_security.pin_hash`; plaintext PINs are never written to the database. Do not reuse real customer credentials or set `APP_MODE` to production; production mode is intentionally disabled.

## Adapter mapping

`SecureBankDatasetRepository` maps the supplied tables into the existing service records. It enforces customer ownership in every query, joins transactions through owned accounts, maps integer paise without floating-point conversion, and writes card blocks/disputes to the local database copy. The local database copy is mutable during demos. Re-copy the source `.db` to reset it.

The adapter uses `customers`, `accounts`, `transactions`, `upi_payments`, `upcoming_payments`, `cards`, `credit_card_statements`, `loans`, `fraud_alerts`, `customer_offers`, `product_offers`, and `consents`. CSV/JSON files are exports and need not be uploaded separately.

## Persistent policy search index

Approved Markdown policy chunks are indexed with FAISS and stored under `D:\HCL_Hackathon\runtime\faiss\`. `policies.faiss` is the vector index; `vectorizer.json` stores the local TF-IDF vocabulary and IDF weights; `manifest.json` fingerprints the approved sources and settings. FastAPI reuses this index on restart and rebuilds it if the policy sources or embedding configuration change. The directory is Git-ignored. To force a clean rebuild, stop FastAPI, remove `runtime\faiss`, and start it again.
