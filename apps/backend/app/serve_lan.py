"""HTTP + HTTPS listeners sharing one application, GPU queue and lifespan."""
import asyncio
from contextlib import contextmanager
from pathlib import Path

import uvicorn

from .core import ROOT
from .main import app


class SharedServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self):
        # asyncio.run owns Ctrl+C and cancels this process's listeners together.
        yield


async def serve():
    certificate_dir = Path(ROOT) / 'data/certs'
    common = dict(app=app, lifespan='off',
                  ws_max_size=32768, limit_concurrency=64)
    servers = [SharedServer(uvicorn.Config(**common, host='127.0.0.1', port=8001)),
               SharedServer(uvicorn.Config(**common, host='0.0.0.0', port=8000,
                            ssl_certfile=str(certificate_dir / 'server.crt'),
                            ssl_keyfile=str(certificate_dir / 'server.key')))]
    async with app.router.lifespan_context(app):
        tasks = [asyncio.create_task(server.serve()) for server in servers]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for server in servers:
                server.should_exit = True
            await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
