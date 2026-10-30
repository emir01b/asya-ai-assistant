"""Local UI controls. No model dependency and no public admin listener."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from apps.agents.store import AgentStore, DEFAULT_SCOPES, SCOPES
from apps.agents.installer import AgentRuntime

class Access(BaseModel):
    enabled: bool

class NewAgent(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scopes: list[str] = Field(default_factory=lambda: list(DEFAULT_SCOPES))
    voice: str = 'asya-default'

def router(directory, runtime=None):
    store = AgentStore(directory)
    runtime = runtime or AgentRuntime(data=directory)
    def local(request: Request):
        if not request.client or request.client.host not in ('127.0.0.1', '::1', 'testclient'):
            raise HTTPException(403, 'Ajan erişimini yalnızca sunucu bilgisayarından yönetin.')
    routes = APIRouter(prefix='/api/v1/agent-admin', dependencies=[Depends(local)])
    @routes.get('')
    def state():
        return dict(enabled=store.enabled(), agents=store.list_agents(), scopes=SCOPES,
                    url='http://127.0.0.1:8002', guide='http://127.0.0.1:8002/.well-known/asya-agent.json')
    @routes.put('/access')
    def access(body: Access):
        if body.enabled:
            if not runtime.refresh()['installed']:
                raise HTTPException(409, 'Önce ajan servisini Kur butonuyla kurun.')
            try:
                runtime.ensure_running()
            except RuntimeError as exc:
                raise HTTPException(503, str(exc)) from None
        store.set_enabled(body.enabled)
        return state()
    @routes.get('/installation')
    def installation():
        return runtime.refresh()
    @routes.post('/installation', status_code=202)
    def install():
        return runtime.install()
    @routes.post('/keys')
    def create(body: NewAgent):
        return store.create_agent(body.name, body.scopes, body.voice)
    @routes.delete('/keys/{identity}')
    def revoke(identity: str):
        if not store.revoke(identity):
            raise HTTPException(404, 'Ajan bulunamadı')
        return {'revoked': True}
    return routes
