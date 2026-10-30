"""Permission catalog shared by discovery, HTTP dispatch and MCP."""
OPERATIONS = {
    'get_status': ('status:read', 'GET', 'system/status', 'Ses motorunun durumunu öğrenir.'),
    'list_voices': ('voices:read', 'GET', 'voices', 'Kullanılabilir ses profillerini listeler.'),
    'generate_speech': ('speech:write', 'POST', None, 'Metni seslendirme kuyruğuna ekler; iş kimliği döner.'),
    'get_job': ('jobs:own', 'GET', None, 'Kendi işinin durumunu ve ses adresini alır.'),
    'cancel_job': ('jobs:own', 'POST', None, 'Kendi işini iptal eder; çalışan segmentin bitmesi gerekebilir.'),
    'get_audio': ('jobs:own', 'GET', None, 'Tamamlanmış kendi sesini indirir.'),
    'get_settings': ('settings:read', 'GET', 'settings', 'Ses ayarlarını okur.'),
    'unload_tts': ('models:unload', 'POST', 'tts/unload', 'Boştaki ses modelini bellekten çıkarır.'),
    'unload_stt': ('models:unload', 'POST', 'stt/unload', 'Boştaki yazıya dönüştürme modelini çıkarır.'),
    'update_settings': ('settings:write', 'PUT', 'settings', 'Yalnızca dil, varsayılan ses, TTS cihazı ve offline ayarını değiştirir.'),
    'update_voice': ('voices:write', 'PUT', None, 'voice_id, name, language, exaggeration, cfg_weight ile profili düzenler.'),
    'delete_voice': ('voices:delete', 'DELETE', None, 'voice_id ile paylaşılan profili siler.'),
    'delete_job': ('history:delete', 'DELETE', None, 'job_id ile yalnızca kendi tamamlanmış işini siler.'),
    'create_voice': ('voices:write', 'POST', None, 'audio_base64, name, language, consent=true ile izinli örnek kayıttan profil oluşturur (en çok 25 MB).'),
    'transcribe': ('transcription:write', 'POST', None, 'audio_base64 ve language ile sesi yazıya çevirir (en çok 25 MB).'),
}

ARGUMENTS = {
    'generate_speech': {'input': 'required string (1–12000)', 'voice': 'profile id or asya-default', 'response_format': 'mp3 or wav', 'speed': '0.75–1.15', 'language': 'language code, e.g. tr', 'idempotency_key': 'optional unique string'},
    'get_job': {'job_id': 'required id from generate_speech'},
    'cancel_job': {'job_id': 'required id from generate_speech'},
    'get_audio': {'job_id': 'required id from generate_speech', 'format': 'mp3 or wav'},
    'delete_job': {'job_id': 'required id from generate_speech'},
    'delete_voice': {'voice_id': 'required profile id'},
    'update_voice': {'voice_id': 'required profile id', 'name': 'required string', 'language': 'tr', 'exaggeration': '0–2', 'cfg_weight': '0–1'},
    'create_voice': {'audio_base64': 'required base64 encoded audio', 'name': 'required string', 'language': 'tr', 'consent': 'required true, with speaker permission'},
    'transcribe': {'audio_base64': 'required base64 encoded audio', 'language': 'tr'},
    'update_settings': {'language': 'optional language code', 'default_voice': 'optional profile id', 'tts_device': 'cpu or cuda', 'offline': 'boolean'},
}
RESULTS = {'generate_speech': 'id,status,progress,error,audio_url; poll get_job until completed',
           'get_job': 'id,status,progress,error,audio_url', 'cancel_job': 'id,status,progress,error,audio_url',
           'get_audio': 'mime_type,data (base64). Direct job audio endpoint returns binary.',
           'list_voices': 'array of id,name,language; no reference recordings',
           'create_voice': 'id,name,language', 'transcribe': 'text,language,segments'}

def guide(agent=None, enabled=False):
    return dict(name='ASYA', version='1.0', enabled=enabled,
        message='Ajan erişimi açık.' if enabled else 'Ayarlar > Ajan erişimi kapalı. Kullanıcı açmadan erişemezsiniz.',
        authentication='Authorization: Bearer <ajan anahtarı>',
        endpoints={'speech': '/v1/audio/speech', 'operations': '/api/v1/agent/operations/{name}',
                   'mcp': '/mcp'} if enabled and agent else {},
        operations=[dict(name=n, scope=s, description=d, method='POST',
                        endpoint='/api/v1/agent/operations/' + n, arguments=ARGUMENTS.get(n, {}),
                        returns=RESULTS.get(n, 'JSON operation result')) for n,(s,m,p,d) in OPERATIONS.items()
                    if enabled and agent and s in agent['scopes']],
        workflow=['list_voices', 'generate_speech', 'get_job', 'get_audio'] if enabled and agent else [],
        ui={'access': 'Ayarlar > Ajan erişimi', 'voices': 'Ses kütüphanesi', 'speech': 'Stüdyo'},
        errors={'401': 'missing/revoked key', '403': 'access disabled or scope denied', '404': 'not found or owned by another agent',
                '409': 'not ready, busy or idempotency conflict', '422': 'invalid arguments', '429': 'queue full',
                '503': 'backend unavailable', '504': 'generation still running; poll returned job_id'},
        speech_schema=__import__('apps.agents.service', fromlist=['Speech']).Speech.model_json_schema() if enabled and agent else None,
        example={'operation': 'generate_speech', 'arguments': {'input': 'Merhaba, ben Ali.', 'voice': 'asya-default'} } if enabled and agent else None)
