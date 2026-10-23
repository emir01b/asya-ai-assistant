from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit
from typing import Literal
from pydantic import BaseModel, Field, field_validator

from .prompts import DEFAULT_SYSTEM_PROMPT

LANGUAGES = ['ar','da','de','el','en','es','fi','fr','he','hi','it','ja','ko','ms','nl','no','pl','pt','ru','sv','sw','tr','zh']


class Generation(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    voice_id: str | None = None
    language: str = 'tr'
    exaggeration: float = Field(default=0.5, ge=0, le=2)
    cfg_weight: float = Field(default=0.5, ge=0, le=1)
    provider: str = Field(default='chatterbox', pattern=r'^[a-z0-9-]{1,40}$')
    normalize: bool = False
    min_segment_chars: int = Field(default=0, ge=0, le=200)
    speech_rate: float = Field(default=1.0, ge=0.75, le=1.15)
    trailing_pause_ms: int = Field(default=0, ge=0, le=1000)

    @field_validator('text')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Metin boş olamaz.')
        return value.strip()

    @field_validator('language')
    @classmethod
    def language_supported(cls, value):
        if value not in LANGUAGES:
            raise ValueError('Desteklenmeyen dil.')
        return value


class Settings(BaseModel):
    lm_url: str = 'http://127.0.0.1:1234/v1'
    llm_model: str = Field(default='', max_length=300)
    temperature: float = Field(default=0.7, ge=0, le=2)
    system_prompt: str = Field(default=DEFAULT_SYSTEM_PROMPT, max_length=12000)
    chat_speech_rate: float = Field(default=0.9, ge=0.75, le=1.15)
    offline: bool = True
    tts_device: Literal['cuda','cpu'] = 'cuda'
    stt_device: Literal['cuda','cpu'] = 'cuda'
    stt_model: str = Field(default='large-v3-turbo', max_length=200, pattern=r'^[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_.-]+)?$')
    stt_cpu_fallback: bool = True
    language: str = 'tr'
    default_voice: str = ''
    vad_threshold: float = Field(default=0.018, ge=0.001, le=0.3)
    vad_silence_ms: int = Field(default=1000, ge=300, le=3000)
    microphone_id: str = Field(default='', max_length=500)
    output_id: str = Field(default='', max_length=500)
    debug: bool = False

    @field_validator('lm_url')
    @classmethod
    def local_url(cls, value):
        url = urlsplit(value)
        host = url.hostname or ''
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == 'localhost'
        if url.scheme != 'http' or not local or url.username or url.password or url.query or url.fragment:
            raise ValueError('LM Studio adresi yerel HTTP adresi olmalı (localhost / 127.0.0.1).')
        return value.rstrip('/')


class Chat(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None
    model: str | None = Field(default=None, max_length=300)
    voice_id: str | None = None
    speak: bool = True


class VoiceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    language: str = 'tr'
    exaggeration: float = Field(default=0.5, ge=0, le=2)
    cfg_weight: float = Field(default=0.5, ge=0, le=1)

    @field_validator('name')
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError('Profil adı boş olamaz.')
        return value.strip()

    @field_validator('language')
    @classmethod
    def supported(cls, value):
        if value not in LANGUAGES:
            raise ValueError('Desteklenmeyen dil.')
        return value


class ConversationCreate(BaseModel):
    title: str = Field(default='Yeni konuşma', min_length=1, max_length=100)


class Segment(BaseModel):
    index: int
    text: str
    asset_id: str
    duration: float
    generation_seconds: float
    ready_seconds: float


class Metrics(BaseModel):
    total_seconds: float | None = None
    synthesis_seconds: float | None = None
    duration: float | None = None
    first_audio_seconds: float | None = None
    rtf: float | None = None
    peak_vram_mb: float | None = None
    model_load_seconds: float | None = None
    queue_seconds: float | None = None


class Job(BaseModel):
    id: str
    created_at: str
    text: str
    voice_id: str | None
    language: str
    provider: str
    exaggeration: float
    cfg_weight: float
    speech_rate: float = 1.0
    trailing_pause_ms: int = 0
    status: Literal['queued','running','cancelling','cancelled','completed','failed']
    progress: float
    segments: list[Segment]
    error: str | None
    metrics: Metrics
    asset_id: str | None


class Voice(BaseModel):
    id: str
    name: str
    language: str
    asset_id: str
    duration: float
    sample_rate: int
    consent: bool
    exaggeration: float
    cfg_weight: float
    created_at: str
