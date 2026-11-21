from fastmcp import Client
from dotenv import load_dotenv
import os
load_dotenv()

MCP_PORT = os.getenv('MCP_PORT', '9096')
MCP_HOST = os.getenv('MCP_HOST', '127.0.0.1')
url = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
client = Client(url, timeout=35)
