from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.service import BankingService
from app.models import ChatInput, PinInput, ConfirmInput, StrictModel

def create_app(service=None):
    app = FastAPI(title='SecureBank AI Assistant',docs_url=None,redoc_url=None)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
    app.state.service = service or BankingService()

    @app.exception_handler(PermissionError)
    async def denied(request, exc):
        return JSONResponse(status_code=403,content={'detail':str(exc)})

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Framework validation details can echo a supplied PIN; return no input values.
        return JSONResponse(status_code=422,content={'detail':'Invalid request format'})

    @app.middleware('http')
    async def secure_headers(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    def token(authorization: str=Header(default='')):
        if not authorization.startswith('Bearer '):
            raise HTTPException(401,'Trusted session required')
        value=authorization[7:]; app.state.service.sessions.get(value)
        return value

    @app.get('/health')
    def health():
        return {'status':'ok','mode':app.state.service.settings.mode,'router':app.state.service.settings.router_mode,'repository':app.state.service.settings.repository}

    @app.get('/dev/customers')
    def development_customers(request:Request):
        if app.state.service.settings.mode != 'development' or request.client.host not in ('127.0.0.1','::1','testclient'):
            raise PermissionError('Development identity list is local-only')
        repo=app.state.service.repository
        return {'customer_ids':repo.customer_ids() if hasattr(repo,'customer_ids') else []}

    class DevIdentity(StrictModel):
        customer_id: str = 'C1001'

    @app.post('/dev/session')
    def development_identity(body:DevIdentity,request:Request):
        if request.headers.get('origin'):
            raise PermissionError('Browser-origin session creation denied')
        value=app.state.service.sessions.issue_development(body.customer_id,request.client.host)
        return {'token':value,'simulated':True,'customer_id':body.customer_id}

    @app.post('/conversations')
    def new_conversation(t=Depends(token)):
        return {'conversation_id':app.state.service.conversation(t)}

    @app.get('/conversations')
    def conversations(t=Depends(token)):
        session=app.state.service.sessions.get(t)
        return [{'id':cid,'title':next((m['content'][:50] for m in msgs if m['role']=='user'),'New conversation')} for cid,msgs in session.conversations.items()]

    @app.get('/conversations/{cid}')
    def history(cid:str,t=Depends(token)):
        return app.state.service.history(t,cid)

    @app.delete('/conversations/{cid}')
    def clear(cid:str,t=Depends(token)):
        app.state.service.clear(t,cid); return {'status':'cleared'}

    @app.post('/chat')
    def chat(body:ChatInput,t=Depends(token)):
        return app.state.service.chat(t,body.conversation_id,body.message)

    @app.post('/verify-pin')
    def verify(body:PinInput,t=Depends(token)):
        return app.state.service.verify(t,body.request_id,body.pin)

    @app.post('/confirm')
    def confirm(body:ConfirmInput,t=Depends(token)):
        return app.state.service.confirm(t,body.request_id,body.confirmed)
    return app

# Uvicorn factory avoids import-time state in tests.
