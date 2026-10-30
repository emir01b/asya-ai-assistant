"""MCP stdio adapter. Token comes from environment, never command-line arguments."""
import os
import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

server = MCPServer('ASYA', instructions='Önce get_capabilities çağırın.')

async def request(path, body=None):
    token = os.environ.get('ASYA_AGENT_TOKEN', '')
    if not token and body is not None:
        raise ToolError('ASYA_AGENT_TOKEN gerekli')
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8002', trust_env=False,
                                 headers={'Authorization': f'Bearer {token}'}, timeout=330) as client:
        response = await (client.get(path) if body is None else client.post(path, json=body))
        if response.is_error:
            raise ToolError(str(response.json().get('detail', 'ASYA request failed')))
        result = response.json()
        return result

@server.tool()
async def get_capabilities() -> dict:
    return await request('/.well-known/asya-agent.json')

@server.tool()
async def execute(operation: str, arguments: dict | None = None) -> dict:
    """Execute a permitted operation from get_capabilities."""
    if not operation.replace('_', '').isalnum():
        raise ValueError('Invalid operation')
    return await request('/api/v1/agent/operations/' + operation, arguments or {})

@server.resource('asya://guide')
async def guide() -> dict:
    return await get_capabilities()

if __name__ == '__main__':
    server.run(transport='stdio')
