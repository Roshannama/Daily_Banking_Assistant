from fastapi.testclient import TestClient
from app.api.main import create_app

def test_http_flow_and_validation_redaction(service,credential):
    client=TestClient(create_app(service))
    assert client.post('/chat',json={'message':'My balance','conversation_id':'fake'}).status_code==401
    token=client.post('/dev/session',json={'customer_id':'C1001'}).json()['token']
    h={'Authorization':'Bearer '+token}
    cid=client.post('/conversations',headers=h).json()['conversation_id']
    p=client.post('/chat',headers=h,json={'conversation_id':cid,'message':'My balance'}).json()
    bad=client.post('/verify-pin',headers=h,json={'request_id':p['request_id'],'pin':'sensitive-overlong-123456789'})
    assert bad.status_code==422 and 'sensitive' not in bad.text
    r=client.post('/verify-pin',headers=h,json={'request_id':p['request_id'],'pin':credential})
    assert r.json()['answer_type']=='retrieved_fact'
    assert r.headers['cache-control']=='no-store'

def test_browser_origin_cannot_bootstrap_identity(service):
    c=TestClient(create_app(service))
    assert c.post('/dev/session',headers={'Origin':'https://evil.example'},json={'customer_id':'C1001'}).status_code==403
