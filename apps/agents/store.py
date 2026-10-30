"""Independent agent credentials and operation ownership."""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

DEFAULT_SCOPES = ['status:read', 'voices:read', 'speech:write', 'jobs:own']
SCOPES = DEFAULT_SCOPES + ['transcription:write', 'voices:write', 'voices:delete',
                          'settings:read', 'settings:write', 'models:unload', 'history:delete']


class AgentStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'gateway.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS control(id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL);
                INSERT OR IGNORE INTO control VALUES(1,0);
                CREATE TABLE IF NOT EXISTS agents(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, digest TEXT UNIQUE NOT NULL,
                    scopes TEXT NOT NULL, voice TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS jobs(
                    id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, upstream_id TEXT,
                    idempotency_key TEXT, fingerprint TEXT NOT NULL, state TEXT NOT NULL,
                    UNIQUE(agent_id, idempotency_key));
            ''')

    def enabled(self):
        with self.connect() as db:
            return bool(db.execute('SELECT enabled FROM control WHERE id=1').fetchone()[0])

    def set_enabled(self, enabled):
        with self.connect() as db:
            db.execute('UPDATE control SET enabled=? WHERE id=1', (int(enabled),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_agent(self, name, scopes=None, voice='asya-default'):
        scopes = DEFAULT_SCOPES if scopes is None else scopes
        if not name.strip() or len(name) > 80 or set(scopes) - set(SCOPES):
            raise ValueError('Invalid agent name or scopes')
        if 'speech:write' in scopes and 'jobs:own' not in scopes:
            raise ValueError('Speech generation requires jobs:own')
        token = 'asya_' + secrets.token_urlsafe(32)
        identity = uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO agents(id,name,digest,scopes,voice) VALUES(?,?,?,?,?)',
                       (identity, name.strip(), hashlib.sha256(token.encode()).hexdigest(),
                        json.dumps(sorted(set(scopes))), voice))
        return dict(id=identity, name=name.strip(), scopes=scopes, voice=voice, token=token)

    def authenticate(self, token):
        with self.connect() as db:
            row = db.execute('SELECT id,name,scopes,voice FROM agents WHERE digest=? AND revoked=0',
                             (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result['scopes'] = json.loads(result['scopes'])
        return result

    def list_agents(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,name,scopes,voice,revoked FROM agents ORDER BY rowid').fetchall()
        return [dict(row) | {'scopes': json.loads(row['scopes'])} for row in rows]

    def revoke(self, identity):
        with self.connect() as db:
            return db.execute('UPDATE agents SET revoked=1 WHERE id=?', (identity,)).rowcount == 1

    def reserve(self, agent_id, fingerprint, key=None):
        """Persist intent before submission. An ambiguous submission is never retried."""
        identity = uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if key:
                row = db.execute('SELECT * FROM jobs WHERE agent_id=? AND idempotency_key=?',
                                 (agent_id, key)).fetchone()
                if row:
                    if row['fingerprint'] != fingerprint:
                        raise ValueError('Idempotency key already used for different input')
                    return dict(row), False
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)',
                       (identity, agent_id, None, key, fingerprint, 'submitting'))
            row = db.execute('SELECT * FROM jobs WHERE id=?', (identity,)).fetchone()
        return dict(row), True

    def submitted(self, identity, upstream_id):
        with self.connect() as db:
            db.execute('UPDATE jobs SET upstream_id=?,state=? WHERE id=?',
                       (upstream_id, 'submitted', identity))

    def own_job(self, identity, agent_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND agent_id=?',
                             (identity, agent_id)).fetchone()
        return dict(row) if row else None

    def jobs(self, agent_id):
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                'SELECT * FROM jobs WHERE agent_id=? ORDER BY rowid DESC LIMIT 200', (agent_id,))]
