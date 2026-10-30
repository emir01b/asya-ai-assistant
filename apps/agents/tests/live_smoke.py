"""Opt-in real engine smoke test; does not enable the user's gateway."""
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from apps.agents.main import create_app

def main():
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Path(directory))
        store = app.state.store
        agent = store.create_agent('Ali canlı bağlantı testi')
        store.set_enabled(True)
        with TestClient(app, base_url='http://127.0.0.1:8002') as client:
            response = client.post('/v1/audio/speech', headers={'Authorization': 'Bearer ' + agent['token']},
                json={'input': 'Merhaba, ben Ali. Ajan bağlantısı çalışıyor.', 'response_format': 'wav'})
            if response.status_code != 200:
                raise RuntimeError(f'{response.status_code}: {response.text}')
            assert response.content[:4] == b'RIFF'
            assert len(response.content) > 1000
            target = Path('data/agent-smoke-ali.wav')
            target.write_bytes(response.content)
            print(f'LIVE WAV OK: {len(response.content)} bytes; {target.resolve()}')

if __name__ == '__main__':
    main()
