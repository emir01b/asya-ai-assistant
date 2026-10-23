from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .prompts import DEFAULT_SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.getenv('VOICE_DATA_DIR', str(ROOT / 'data'))).resolve()


def uid() -> str:
    return uuid.uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULTS = dict(
    lm_url='http://127.0.0.1:1234/v1', llm_model='', temperature=0.7,
    system_prompt=DEFAULT_SYSTEM_PROMPT, chat_speech_rate=0.9,
    offline=True, tts_device='cuda', stt_device='cuda', stt_model='large-v3-turbo',
    stt_cpu_fallback=True, language='tr', default_voice='', vad_threshold=0.018,
    vad_silence_ms=1000, microphone_id='', output_id='', debug=False,
)


class Store:
    def __init__(self, directory: Path = DATA):
        self.root = directory
        for folder in ('voices', 'recordings', 'generations', 'database'):
            (directory / folder).mkdir(parents=True, exist_ok=True)
        self.path = directory / 'database' / 'studio.sqlite3'
        self.lock = threading.RLock()
        self.migrate()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def migrate(self):
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version < 1:
                db.executescript('''
                CREATE TABLE records(kind TEXT NOT NULL,id TEXT NOT NULL,body TEXT NOT NULL,
                    created_at TEXT NOT NULL,PRIMARY KEY(kind,id));
                CREATE INDEX records_kind_date ON records(kind,created_at DESC);
                PRAGMA user_version=1;
                ''')
    def recover_jobs(self):
        # Only the owning backend startup recovers jobs, never a read-only Store.
        for job in self.list('job'):
            if job['status'] in ('queued', 'running', 'cancelling'):
                self.put('job', {**job, 'status': 'failed', 'error': 'Backend yeniden başlatıldı.'})

    def put(self, kind: str, body: dict) -> dict:
        body = {**body}
        body.setdefault('id', uid())
        body.setdefault('created_at', now())
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO records VALUES(?,?,?,?) ON CONFLICT(kind,id) '
                       'DO UPDATE SET body=excluded.body',
                       (kind, body['id'], json.dumps(body, ensure_ascii=False), body['created_at']))
        return body

    def get(self, kind: str, key: str) -> dict | None:
        with self.connect() as db:
            row = db.execute('SELECT body FROM records WHERE kind=? AND id=?', (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind: str, limit: int = 200) -> list[dict]:
        with self.connect() as db:
            rows = db.execute('SELECT body FROM records WHERE kind=? ORDER BY created_at DESC LIMIT ?',
                              (kind, limit)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete(self, kind: str, key: str):
        with self.lock, self.connect() as db:
            db.execute('DELETE FROM records WHERE kind=? AND id=?', (kind, key))

    def count(self, kind: str) -> int:
        with self.connect() as db:
            return db.execute('SELECT COUNT(*) FROM records WHERE kind=?', (kind,)).fetchone()[0]

    def settings(self):
        return {**DEFAULTS, **(self.get('settings', 'app') or {})}

    def asset(self, key: str) -> Path:
        record = self.get('asset', key)
        if not record:
            raise ValueError('Ses dosyası bulunamadı.')
        path = (self.root / record['path']).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise ValueError('Geçersiz ses dosyası.')
        return path

    def add_asset(self, path: Path, **metadata):
        return self.put('asset', dict(path=str(path.relative_to(self.root)), **metadata))

    def error(self, source: str, message: str):
        return self.put('error', dict(source=source, message=message))
