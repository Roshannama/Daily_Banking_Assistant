-- Optional canonical adapter contract FOR INTEGRATION TESTS ONLY.
-- Do not execute against teammate tables without agreeing mappings.
CREATE TABLE banking_customers(customer_id TEXT PRIMARY KEY, pin_hash TEXT NOT NULL);
CREATE TABLE banking_records(
 customer_id TEXT NOT NULL, kind TEXT NOT NULL, resource_id TEXT NOT NULL,
 payload TEXT NOT NULL CHECK(json_valid(payload)),
 PRIMARY KEY(customer_id,kind,resource_id)
);
CREATE TABLE banking_disputes(
 customer_id TEXT NOT NULL, transaction_id TEXT NOT NULL,
 dispute_id TEXT NOT NULL UNIQUE, idempotency_key TEXT NOT NULL,
 UNIQUE(customer_id,transaction_id)
);
CREATE TABLE banking_audit(id INTEGER PRIMARY KEY, event TEXT NOT NULL CHECK(json_valid(event)));
