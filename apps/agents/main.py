"""Separate authenticated gateway; shares only control/ownership SQLite with local UI."""
import base64
import os
from contextvars import ContextVar
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.server.mcpserver.exceptions import ToolError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from .store import AgentStore
from .service import AgentService, Speech
from .catalog import OPERATIONS, guide

current_token = ContextVar('agent_token', default='')

def create_app(directory=None, transport=None, backend=None):
    directory = directory or Path(os.getenv('VOICE_DATA_DIR', str(Path(__file__).resolve().parents[2] / 'data'))) / 'agents'
    store = AgentStore(directory)
    service = AgentService(store, backend or os.getenv('ASYA_BACKEND_URL', 'http://127.0.0.1:8000'), transport)
    def authorize(token):
        if not store.enabled():
            raise HTTPException(403, {'code': 'agent_access_disabled', 'message': guide()['message']})
        agent = store.authenticate(token)
        if not agent:
            raise HTTPException(401, 'Geçerli ajan anahtarı gerekli')
        return agent
    service.guard = lambda: authorize(current_token.get())
    async def dispatch(name, arguments=None):
        agent = authorize(current_token.get())
        args = arguments or {}
        if name not in OPERATIONS:
            raise HTTPException(404, 'Unknown operation')
        scope, method, path, _ = OPERATIONS[name]
        service.require(agent, scope)
        if name in ('create_voice', 'transcribe'):
            try:
                recording = base64.b64decode(args.get('audio_base64', ''), validate=True)
            except (ValueError, TypeError):
                raise HTTPException(400, 'Invalid base64 audio') from None
            if not recording or len(recording) > 25 * 1024 * 1024:
                raise HTTPException(413, 'Audio must be between 1 byte and 25 MB')
            data = {'language': args.get('language', 'tr')}
            if name == 'create_voice':
                if args.get('consent') is not True:
                    raise HTTPException(400, 'Explicit consent=true required')
                data.update(name=args.get('name', ''), consent='true')
            result = (await service.upstream('POST', 'voices' if name == 'create_voice' else 'stt/transcribe',
                data=data, files={'file': ('recording.wav', recording, 'application/octet-stream')})).json()
            if name == 'create_voice':
                return {k: result[k] for k in ('id', 'name', 'language')}
            return {k: result[k] for k in ('text', 'language', 'segments') if k in result}
        if name == 'update_settings':
            allowed = {'language', 'default_voice', 'tts_device', 'offline'}
            if set(args) - allowed:
                raise HTTPException(400, 'Unsupported settings')
            settings = (await service.upstream('GET', 'settings')).json()
            result = (await service.upstream('PUT', 'settings', json=settings | args)).json()
            return {k: result[k] for k in allowed}
        if name in ('update_voice', 'delete_voice'):
            args = dict(args)
            identity = service.identifier(args.pop('voice_id', ''))
            if name == 'update_voice':
                if set(args) - {'name', 'language', 'exaggeration', 'cfg_weight'}:
                    raise HTTPException(400, 'Unsupported voice settings')
                result = (await service.upstream('PUT', 'voices/' + identity, json=args)).json()
                return {k: result[k] for k in ('id', 'name', 'language')}
            return (await service.upstream('DELETE', 'voices/' + identity)).json()
        if name == 'delete_job':
            record = service.owned(agent, args.get('job_id', ''))
            return (await service.upstream('DELETE', 'tts/history/' + record['upstream_id'])).json()
        if name == 'generate_speech':
            args = dict(args)
            key = args.pop('idempotency_key', None)
            try:
                speech = Speech(**args)
            except ValidationError:
                raise HTTPException(422, 'Invalid speech arguments; see speech_schema') from None
            return await service.generate(agent, speech, key)
        if name == 'list_voices':
            return await service.voices(agent)
        if name in ('get_job', 'cancel_job', 'get_audio'):
            identity = service.identifier(args.get('job_id', ''))
            if name == 'get_audio':
                result = await service.audio(agent, identity, args.get('format', 'mp3'))
                return dict(mime_type=result.headers.get('content-type'), data=base64.b64encode(result.content).decode())
            return await (service.job(agent, identity) if name == 'get_job' else service.cancel(agent, identity))
        result = (await service.upstream(method, path)).json()
        if name == 'get_status':
            return {k: result[k] for k in ('tts', 'stt', 'offline') if k in result}
        if name == 'get_settings':
            return {k: result[k] for k in ('language', 'default_voice', 'tts_device', 'offline') if k in result}
        return result
    mcp = MCPServer('ASYA', instructions='Önce get_capabilities kullanın. Yalnızca izin verilen işlemleri çağırın.')
    @mcp.tool()
    def get_capabilities() -> dict:
        return guide(authorize(current_token.get()), True)
    @mcp.tool()
    async def execute(operation: str, arguments: dict | None = None) -> dict:
        """Run an operation listed by get_capabilities. Speech takes input/voice; jobs take job_id."""
        try:
            return await dispatch(operation, arguments)
        except HTTPException as exc:
            raise ToolError(f'{exc.status_code}: {exc.detail}') from None
    @mcp.resource('asya://guide')
    def resource() -> dict:
        return get_capabilities()
    hosts = ['localhost', '127.0.0.1', '[::1]']
    lan_ip = os.getenv('ASYA_AGENT_LAN_IP')
    if lan_ip:
        hosts.append(lan_ip)
    mcp_app = mcp.streamable_http_app(stateless_http=True, json_response=True,
        max_request_body_size=36 * 1024 * 1024,
        transport_security=TransportSecuritySettings(allowed_hosts=[h + ':*' for h in hosts] + hosts))
    @asynccontextmanager
    async def lifespan(app):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield
        await service.client.aclose()
    app = FastAPI(title='ASYA Agent API', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.service, app.state.store = service, store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    @app.middleware('http')
    async def security(request: Request, call_next):
        if request.headers.get('origin') or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Browser cross-origin access denied'}, status_code=403)
        token = request.headers.get('authorization', '').removeprefix('Bearer ')
        context = current_token.set(token)
        try:
            if request.url.path != '/.well-known/asya-agent.json':
                authorize(token)
                if lan_ip:
                    status = (await service.upstream('GET', 'system/status')).json()
                    if status.get('network', {}).get('lan_enabled') is not False:
                        raise HTTPException(503, 'Ana backend LAN modu açık; ajan erişimi engellendi.')
            try:
                length = int(request.headers.get('content-length', '0'))
            except ValueError:
                raise HTTPException(400, 'Invalid Content-Length') from None
            if length > 36 * 1024 * 1024:
                raise HTTPException(413, 'Request too large')
            receive = request._receive
            received = 0
            async def limited_receive():
                nonlocal received
                message = await receive()
                received += len(message.get('body', b''))
                if received > 36 * 1024 * 1024:
                    raise HTTPException(413, 'Request too large')
                return message
            request._receive = limited_receive
            response = await call_next(request)
            if request.url.path != '/.well-known/asya-agent.json':
                authorize(token)  # Do not return audio after a disable/revocation during synthesis.
            response.headers['Cache-Control'] = 'no-store'
            return response
        except HTTPException as exc:
            return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
        finally:
            current_token.reset(context)
    @app.get('/.well-known/asya-agent.json')
    async def discovery():
        return guide(store.authenticate(current_token.get()), store.enabled())
    @app.post('/api/v1/agent/operations/{name}')
    async def operation(name: str, body: dict):
        return await dispatch(name, body)
    @app.post('/api/v1/agent/speech', status_code=202)
    async def generate(body: Speech, request: Request):
        return await service.generate(authorize(current_token.get()), body, request.headers.get('idempotency-key'))
    @app.get('/api/v1/agent/jobs/{identity}')
    async def job(identity: str):
        return await service.job(authorize(current_token.get()), identity)
    @app.post('/api/v1/agent/jobs/{identity}/cancel')
    async def cancel(identity: str):
        return await service.cancel(authorize(current_token.get()), identity)
    @app.get('/api/v1/agent/jobs/{identity}/audio')
    async def audio(identity: str, format: str = 'mp3'):
        result = await service.audio(authorize(current_token.get()), identity, format)
        return Response(result.content, media_type='audio/wav' if format == 'wav' else 'audio/mpeg')
    @app.post('/v1/audio/speech')
    async def speech(body: Speech, request: Request):
        agent = authorize(current_token.get())
        job = await service.generate(agent, body, request.headers.get('idempotency-key'))
        job = await service.wait(agent, job['id'])
        if job['status'] != 'completed':
            raise HTTPException(409, job)
        return await audio(job['id'], body.response_format)
    app.mount('/', mcp_app)
    return app

app = create_app()
