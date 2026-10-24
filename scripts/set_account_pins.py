"""Provision a unique local Argon2 PIN for each account in the demo SQLite DB."""
import argparse
import hashlib
import getpass
import sqlite3
from pathlib import Path

from argon2 import PasswordHasher

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'runtime' / 'data' / 'securebank_demo.db'


def ensure_schema(con):
    con.execute('''CREATE TABLE IF NOT EXISTS account_security (
        account_id TEXT PRIMARY KEY REFERENCES accounts(account_id) ON DELETE CASCADE,
        pin_hash TEXT,
        pin_updated_at TEXT,
        CHECK(pin_hash IS NULL OR pin_hash LIKE '$argon2id$%')
    )''')
    con.execute('''INSERT OR IGNORE INTO account_security(account_id)
        SELECT account_id FROM accounts''')
    con.commit()


def valid_pin(pin):
    return pin.isascii() and pin.isdigit() and 4 <= len(pin) <= 12


def main():
    parser = argparse.ArgumentParser(description='Set unique PINs for local demo accounts (only salted hashes are stored).')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB, help='SQLite demo database path')
    parser.add_argument('--account-id', help='Provision one account; by default all accounts without a PIN are handled')
    parser.add_argument('--initialize-only', action='store_true', help='Create the account_security table and empty rows without prompting for PINs')
    args = parser.parse_args()
    if not args.db.is_file():
        raise SystemExit(f'Database not found: {args.db}')

    hasher = PasswordHasher()
    with sqlite3.connect(args.db, timeout=10) as con:
        con.execute('PRAGMA foreign_keys=ON')
        ensure_schema(con)
        if args.initialize_only:
            total = con.execute('SELECT COUNT(*) FROM account_security').fetchone()[0]
            print(f'Account PIN storage initialized for {total} account(s). No PIN values or hashes were added.')
            return
        query = '''SELECT a.account_id, a.customer_id, a.account_number_masked
                   FROM accounts a JOIN account_security s USING(account_id)
                   WHERE s.pin_hash IS NULL'''
        params = ()
        if args.account_id:
            query += ' AND a.account_id=?'
            params = (args.account_id,)
        query += ' ORDER BY a.account_id'
        accounts = con.execute(query, params).fetchall()
        if args.account_id and not accounts:
            exists = con.execute('SELECT 1 FROM accounts WHERE account_id=?', (args.account_id,)).fetchone()
            if not exists:
                raise SystemExit('Account ID was not found.')
            print('That account already has a PIN hash.')
            return
        if not accounts:
            print('All accounts already have PIN hashes.')
            return

        print(f'Setting unique PINs for {len(accounts)} account(s). PIN input is hidden.')
        used_pin_digests = set()
        for account_id, customer_id, masked_number in accounts:
            print(f'\nAccount {account_id} ({masked_number}) for customer {customer_id}')
            while True:
                pin = getpass.getpass('New PIN (4-12 digits): ')
                repeat = getpass.getpass('Repeat PIN: ')
                if pin != repeat or not valid_pin(pin):
                    del pin, repeat
                    print('PIN mismatch or invalid format; try again.')
                    continue
                pin_digest = hashlib.sha256(pin.encode('ascii')).digest()
                duplicate = pin_digest in used_pin_digests
                if duplicate:
                    del pin, repeat
                    print('Each account must have a different PIN; choose another.')
                    continue
                encoded = hasher.hash(pin)
                del pin, repeat
                con.execute('''UPDATE account_security
                    SET pin_hash=?, pin_updated_at=datetime('now')
                    WHERE account_id=? AND pin_hash IS NULL''', (encoded, account_id))
                con.commit()
                used_pin_digests.add(pin_digest)
                del encoded
                print('PIN hash saved.')
                break
        remaining = con.execute('SELECT COUNT(*) FROM account_security WHERE pin_hash IS NULL').fetchone()[0]
        total = con.execute('SELECT COUNT(*) FROM account_security').fetchone()[0]
        print(f'Provisioned hashes: {total - remaining}/{total}; remaining without PIN: {remaining}.')
        print('Only salted Argon2id hashes were stored. Restart FastAPI to apply changes.')


if __name__ == '__main__':
    main()
