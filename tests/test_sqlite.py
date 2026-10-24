import json
import sqlite3
from pathlib import Path
import pytest
from app.data.sqlite_repository import SQLiteBankingRepository
from app.data.repository import RepositoryError

def test_adapter_contract_ownership_idempotency_and_real_write(tmp_path,encoded):
    path=tmp_path/'contract.db'
    with sqlite3.connect(path) as con:
        con.executescript((Path(__file__).resolve().parents[1]/'docs/sqlite_contract.sql').read_text())
        con.execute('INSERT INTO banking_customers VALUES(?,?)',('C1001',encoded))
        for customer,resource,kind,payload in [('C1001','CARD1','cards',{'id':'CARD1','status':'active'}),('C1002','CARD2','cards',{'id':'CARD2','status':'active'}),('C1001','TXN1','transactions',{'id':'TXN1','amount_paise':100})]:
            con.execute('INSERT INTO banking_records VALUES(?,?,?,?)',(customer,kind,resource,json.dumps(payload)))
    repo=SQLiteBankingRepository(str(path))
    assert len(repo.records('C1001','cards'))==1
    assert repo.pin_hash('C1001')==encoded
    assert repo.block_card('C1001','CARD2','k')['status']=='not_found'
    assert repo.block_card('C1001','CARD1','k')['status']=='blocked'
    assert repo.records('C1001','cards')[0]['status']=='blocked'
    first=repo.create_dispute('C1001','TXN1','one')
    assert first==repo.create_dispute('C1001','TXN1','two')
    assert repo.create_dispute('C1002','TXN1','three')['status']=='not_found'
    repo.audit({'trace_id':'test'})

def test_unknown_schema_not_modified(tmp_path):
    path=tmp_path/'teammate.db'
    with sqlite3.connect(path) as con:con.execute('CREATE TABLE unrelated(id INTEGER)')
    with pytest.raises(RepositoryError):SQLiteBankingRepository(str(path))
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('unrelated',)]
