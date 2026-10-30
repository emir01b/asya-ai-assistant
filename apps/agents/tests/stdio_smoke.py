"""Run against an already running disabled local gateway."""
import asyncio
import os
import sys
from pathlib import Path
import httpx
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    with httpx.Client(trust_env=False) as client:
        guide = client.get('http://127.0.0.1:8002/.well-known/asya-agent.json').json()
        assert guide['enabled'] is False
        assert client.post('http://127.0.0.1:8002/v1/audio/speech', json={'input': 'No synthesis'}).status_code == 403
    parameters = StdioServerParameters(command=sys.executable, args=['-m', 'apps.agents.stdio'],
        cwd=Path(__file__).resolve().parents[3], env=dict(os.environ, ASYA_AGENT_TOKEN='disabled-smoke-placeholder'))
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert {'get_capabilities', 'execute'} <= {tool.name for tool in listing.tools}
            result = await session.call_tool('get_capabilities', {})
            assert not result.is_error
            result = await session.call_tool('execute', {'operation': 'list_voices'})
            assert result.is_error
            print('MCP stdio initialized; tools listed; disabled access correctly rejected')

if __name__ == '__main__':
    asyncio.run(main())
