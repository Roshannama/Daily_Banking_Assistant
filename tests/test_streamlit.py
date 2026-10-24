from urllib.parse import urlsplit
import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from app.api.main import create_app
from app.config import ROOT

def test_native_chat_pin_and_sessions(service,credential,monkeypatch):
    client=TestClient(create_app(service))
    def request(method,url,**kwargs):
        assert kwargs.get('headers',{}).get('Authorization')!='Bearer '
        return client.request(method,urlsplit(url).path,headers=kwargs.get('headers'),json=kwargs.get('json'))
    monkeypatch.setattr(httpx,'request',request)
    ui=AppTest.from_file(str(ROOT/'app/streamlit_app.py'),default_timeout=20).run()
    assert not ui.exception
    assert ui.title[0].value=='SecureBank AI Assistant'
    assert len(ui.text_input)==0
    ui.chat_input[0].set_value('What is UPI?').run()
    assert not ui.exception and len(ui.text_input)==0
    ui.chat_input[0].set_value('My balance').run()
    assert not ui.exception and len(ui.text_input)==1 and service.repository.reads==[]
    ui.text_input[0].set_value(credential)
    next(b for b in ui.button if b.label=='Verify PIN').click().run()
    assert not ui.exception
    assert any('125,100.00' in m.value for m in ui.markdown)
    next(b for b in ui.button if b.label=='New Chat').click().run()
    assert not ui.exception and len(ui.chat_message)==0

def test_native_action_confirmation(service,credential,monkeypatch):
    client=TestClient(create_app(service))
    monkeypatch.setattr(httpx,'request',lambda method,url,**kw:client.request(method,urlsplit(url).path,headers=kw.get('headers'),json=kw.get('json')))
    ui=AppTest.from_file(str(ROOT/'app/streamlit_app.py'),default_timeout=20).run()
    ui.chat_input[0].set_value('Block card CARD0001D').run()
    ui.text_input[0].set_value(credential)
    next(b for b in ui.button if b.label=='Verify PIN').click().run()
    assert not service.repository.writes
    next(b for b in ui.button if b.label=='Confirm action').click().run()
    assert not ui.exception and service.repository.data['C1001']['cards'][0]['status']=='blocked'
