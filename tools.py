from fastmcp import FastMCP
from typing import Optional
from dotenv import load_dotenv
from vectors import vector_manager
load_dotenv()
import os
host = os.getenv('MCP_HOST', '127.0.0.1')
port = int(os.getenv('MCP_PORT', 9096))
mcp = FastMCP("Exam-Bot")


@mcp.tool()
def get_context(query:str,channel_id: Optional[str] = None,author: Optional[str] = None ):
    """
    Get the relevant context regarding a topic or query.
    Arguments: It takes the string to be searched to get enough context related to that query or string or facts. Also the channel_id and author(both are optional)

    Returns:
      It returns a list of dictionary containing the relevant chunks.
    """
    print("using tool")
    result = vector_manager.search_similar_chunks(query,5,channel_id,author)
    print("Response from the tool: ", result)
    print(f"here is the result: {result}")
    return result 

@mcp.tool()
def search_internet():
    
    return 

if __name__ == "__main__":
    print("🚀 Starting MCP server...")
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
        log_level="debug",
    )