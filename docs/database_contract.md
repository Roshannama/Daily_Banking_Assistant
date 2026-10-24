# Supplied dataset and future banking integration

The current local demo uses `SecureBankDatasetRepository` against the supplied fictional dataset copied to `runtime/data/securebank_demo.db`. It reads the dataset's native schema and exposes 50 synthetic customers. See `dataset_setup.md` for setup and reset steps. The dataset's `users.password_hash` fields are login password hashes, not PIN hashes. Per-account PIN hashes are stored in the separate local `account_security` table, using Argon2id; plaintext PINs are never persisted.

The generic `SQLiteBankingRepository` below remains a separate example adapter for a future bank-owned schema. The supplied hackathon dataset does not represent an authoritative or live bank connection.

`BankingRepository` defines customer-scoped record retrieval, PIN-hash lookup, card blocking, dispute creation, and audit persistence. Record kinds: accounts, transactions, upcoming, cards, loans, fraud, offers and consent. Financial fields use integer paise; dates use ISO 8601. Missing rows return not_found; connection or schema errors return data_unavailable.

`SQLiteBankingRepository` implements the explicit canonical contract in `sqlite_contract.sql`. It checks an existing file and never creates or migrates it. This is a proposed integration interface, not an assumption about another schema. Tests create temporary databases to exercise ownership, real writes and duplicate-dispute constraints. The supplied dataset adapter is separately verified against the actual provided schema and a local copy.

For final mapping and validation, supply:

- Database file or API endpoint and schema/SQL DDL.
- Relationships and ownership columns for every resource.
- Demo customer IDs and fictional sample accounts, transactions, cards, loans, obligations, offers and consents.
- PIN hash algorithm, format and verification interface. Current verifier accepts Argon2id encoded hashes. Do not send real plaintext PINs.
- Access requirements, audit destination, transaction guarantees and idempotency behavior.
- Upstream identity contract: issuer, audience, signature validation, customer claims and revocation.

Adapt `sqlite_repository.py` or implement another repository. Every query and mutation must include the trusted customer ownership predicate. Never derive identity from a chat message or arbitrary header.

After mappings are agreed, set `REPOSITORY=sqlite` and `DATABASE_PATH` in `.env`. The mock `.env` PIN hash is a development fixture; a mapped database supplies each customer's own encoded hash.
