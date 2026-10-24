import os
from pathlib import Path
from urllib.parse import urlsplit
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1]/'.env')
st.set_page_config(page_title='SecureBank AI Assistant',page_icon='🏦')
st.title('SecureBank AI Assistant')
st.caption('Development prototype · Simulated identity and fictional banking records · Not connected to a bank')
BASE=os.getenv('API_URL','http://127.0.0.1:8000')

def api(method,path,body=None):
    token=st.session_state.get('token')
    headers={'Authorization':'Bearer '+token} if token else {}
    try:
        r=httpx.request(method,BASE+path,headers=headers,json=body,timeout=40)
        if r.status_code>=400:
            if r.status_code == 404 and path == '/dev/customers':
                st.error('The SecureBank API on this port is an older build and does not provide the local customer endpoint. Restart FastAPI from this project folder using the current README command, then refresh this page.')
                st.stop()
            st.error(r.json().get('detail','Request failed'))
            st.stop()
        return r.json()
    except httpx.HTTPError as exc:
        endpoint=urlsplit(BASE)
        st.error(f'Backend unavailable ({type(exc).__name__}) at {endpoint.hostname}:{endpoint.port}. Start FastAPI using the README command.'); st.stop()

with st.sidebar:
    st.header('Conversations')
    known_customers=api('GET','/dev/customers').get('customer_ids',[])
    if not known_customers:
        st.error('No local demo customers are available.'); st.stop()
    customer=st.selectbox('Local test identity',known_customers)
    st.caption('Development only. Every personal request requires a server-verified PIN.')
    if customer!=st.session_state.get('customer'):
        st.session_state.clear()
        st.session_state.customer=customer
        st.session_state.token=api('POST','/dev/session',{'customer_id':customer})['token']
        st.session_state.cid=api('POST','/conversations')['conversation_id']
        st.rerun()
    if st.button('New Chat'):
        st.session_state.cid=api('POST','/conversations')['conversation_id']; st.rerun()
    conversations=api('GET','/conversations')
    labels={r['id']:r['title'] for r in conversations}
    ids=list(labels)
    chosen=st.selectbox('Previous conversations',ids,index=ids.index(st.session_state.cid),format_func=lambda cid:labels[cid])
    if chosen!=st.session_state.cid:
        st.session_state.cid=chosen; st.rerun()
    if st.button('Clear Chat'):
        api('DELETE','/conversations/'+chosen); st.rerun()
    st.caption('For the supplied dataset use scripts/set_account_pins.py; mock mode uses scripts/set_demo_pin.py. Never type a PIN in chat.')

messages=api('GET','/conversations/'+st.session_state.cid)
for m in messages:
    with st.chat_message(m['role']):
        if m['role']=='user':
            st.write(m['content'])
        else:
            r=m['response']; st.write(r['answer'])
            for alert in r.get('alerts', []):
                message = f"{alert['message']} Transaction: {alert['transaction_id']} · Risk: {alert['risk_level']} · Status: {alert['status']}"
                if alert['severity'] == 'critical':
                    st.error('🚨 ' + message)
                else:
                    st.warning('⚠️ ' + message)
            with st.expander('Citations, tools and trace'):
                st.json({k:r[k] for k in ('citations','tools_used','trace_id','action_status')})

last=messages[-1].get('response',{}) if messages else {}
if last.get('answer_type')=='pin_required':
    with st.form('secure_pin',clear_on_submit=True):
        pin=st.text_input('PIN for this request',type='password')
        submitted=st.form_submit_button('Verify PIN')
    if submitted:
        result=api('POST','/verify-pin',{'request_id':last['request_id'],'pin':pin})
        del pin
        if result['answer_type']=='pin_required':
            st.error(result['answer'])
        else:
            st.rerun()
elif last.get('answer_type')=='pending_confirmation':
    left,right=st.columns(2)
    for col,label,approved in [(left,'Confirm action',True),(right,'Cancel',False)]:
        if col.button(label):
            result=api('POST','/confirm',{'request_id':last['request_id'],'confirmed':approved})
            if result['answer_type']=='pin_required':
                st.warning(result['answer'])
                # Show a fresh PIN form on next render without retaining any credential.
                st.session_state.reverify=last['request_id']
            else:
                st.rerun()
    if st.session_state.get('reverify')==last.get('request_id'):
        with st.form('reverify',clear_on_submit=True):
            fresh=st.text_input('Fresh PIN',type='password')
            if st.form_submit_button('Verify again'):
                result=api('POST','/verify-pin',{'request_id':last['request_id'],'pin':fresh})
                if result['answer_type']=='pending_confirmation':
                    st.session_state.pop('reverify',None); st.rerun()
                else:
                    st.error(result['answer'])

if prompt:=st.chat_input('Ask about banking, your account, or a policy'):
    api('POST','/chat',{'conversation_id':st.session_state.cid,'message':prompt}); st.rerun()
