"""Authenticated adapters call the running backend, never its model modules."""
from __future__ import annotations

import asyncio
import hashlib
import json
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .store import AgentStore


class Speech(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: str = 'chatterbox-multilingual-v3'
    input: str = Field(min_length=1, max_length=12000)
    voice: str = 'asya-default'
    response_format: str = 'mp3'
    speed: float = Field(default=1, ge=.75, le=1.15)
    language: str | None = None
    instructions: str | None = None
    stream_format: str = 'audio'


class AgentService:
    def __init__(self, store: AgentStore, backend='http://127.0.0.1:8000', transport=None):
        parsed = urlsplit(backend)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError('Backend must be a loopback HTTP origin')
        self.store = store
        self.client = httpx.AsyncClient(base_url=backend.rstrip('/') + '/api/v1/',
                                       transport=transport, trust_env=False,
                                       follow_redirects=False, timeout=330)
        self.lock = asyncio.Lock()
        self.guard = None

    @staticmethod
    def require(agent, scope):
        if scope not in agent['scopes']:
            raise HTTPException(403, f'Required scope: {scope}')

    async def upstream(self, method, path, **kwargs):
        if self.guard:
            self.guard()
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.HTTPError:
            raise HTTPException(503, 'ASYA backend unavailable') from None
        if response.is_error:
            try:
                detail = response.json().get('detail', 'Backend operation failed')
            except ValueError:
                detail = 'Backend operation failed'
            status = response.status_code
            if status == 400 and isinstance(detail, str) and 'kuyruğu dolu' in detail:
                status = 429
            raise HTTPException(status, detail)
        if response.is_redirect:
            raise HTTPException(502, 'Backend redirects are not accepted')
        return response

    async def voices(self, agent):
        self.require(agent, 'voices:read')
        voices = (await self.upstream('GET', 'voices')).json()
        # Reference recordings are not exposed by a voice metadata permission.
        return [{k: v[k] for k in ('id', 'name', 'language') if k in v} for v in voices]

    async def generate(self, agent, request: Speech, key=None):
        self.require(agent, 'speech:write')
        if request.model != 'chatterbox-multilingual-v3':
            raise HTTPException(400, 'Supported model: chatterbox-multilingual-v3')
        if request.response_format not in ('wav', 'mp3'):
            raise HTTPException(400, 'Supported formats: wav, mp3')
        if request.instructions or request.stream_format != 'audio':
            raise HTTPException(400, 'Instructions and realtime audio streaming are not supported')
        if not request.input.strip():
            raise HTTPException(400, 'Input must contain text')
        if key and len(key) > 200:
            raise HTTPException(400, 'Idempotency-Key exceeds 200 characters')
        fingerprint = hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True).encode()).hexdigest()
        async with self.lock:
            try:
                record, created = self.store.reserve(agent['id'], fingerprint, key)
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from None
            if not created:
                if not record['upstream_id']:
                    raise HTTPException(409, {'code': 'submission_uncertain', 'job_id': record['id'],
                                               'message': 'Do not automatically resubmit this request'})
                return await self.job(agent, record['id'])
            settings = (await self.upstream('GET', 'settings')).json()
            voice = request.voice
            if voice == 'asya-default':
                voice = agent['voice']
            if voice == 'asya-default':
                voice = settings.get('default_voice') or None
            language = request.language
            if voice:
                profile = (await self.upstream('GET', f'voices/{self.identifier(voice)}')).json()
                language = language or profile['language']
            result = (await self.upstream('POST', 'tts/generate', json={
                'text': request.input, 'voice_id': voice, 'language': language or settings['language'],
                'speech_rate': request.speed,
            })).json()
            self.store.submitted(record['id'], result['id'])
            return self.public_job(record['id'], result)

    @staticmethod
    def identifier(value):
        if not value or len(value) > 128 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in value):
            raise HTTPException(400, 'Invalid identifier')
        return value

    def owned(self, agent, identity):
        self.require(agent, 'jobs:own')
        record = self.store.own_job(identity, agent['id'])
        if not record:
            raise HTTPException(404, 'Job not found')
        if not record['upstream_id']:
            raise HTTPException(409, 'Submission has no confirmed backend job')
        return record

    @staticmethod
    def public_job(identity, job):
        return dict(id=identity, status=job['status'], progress=job.get('progress', 0),
                    error=job.get('error'), audio_url=f'/api/v1/agent/jobs/{identity}/audio'
                    if job['status'] == 'completed' else None)

    async def job(self, agent, identity):
        record = self.owned(agent, identity)
        job = (await self.upstream('GET', f"tts/jobs/{record['upstream_id']}")).json()
        return self.public_job(identity, job)

    async def cancel(self, agent, identity):
        record = self.owned(agent, identity)
        job = (await self.upstream('POST', f"tts/jobs/{record['upstream_id']}/cancel")).json()
        return self.public_job(identity, job)

    async def audio(self, agent, identity, format='mp3'):
        if format not in ('mp3', 'wav'):
            raise HTTPException(400, 'Supported formats: wav, mp3')
        record = self.owned(agent, identity)
        job = (await self.upstream('GET', f"tts/jobs/{record['upstream_id']}")).json()
        if job['status'] != 'completed' or not job.get('asset_id'):
            raise HTTPException(409, 'Audio is not ready')
        return await self.upstream('GET', f"audio/{self.identifier(job['asset_id'])}", params={'format': format})

    async def wait(self, agent, identity, timeout=300):
        async def poll():
            while True:
                job = await self.job(agent, identity)
                if job['status'] in ('completed', 'cancelled', 'failed'):
                    return job
                await asyncio.sleep(.25)
        try:
            return await asyncio.wait_for(poll(), timeout)
        except asyncio.TimeoutError:
            raise HTTPException(504, {'job_id': identity, 'poll_url': f'/api/v1/agent/jobs/{identity}'}) from None
