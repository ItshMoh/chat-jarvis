from fastmcp import FastMCP
from typing import Optional
from dotenv import load_dotenv
from vectors import vector_manager
from netsearch import search_web_perplexity
from tidb import db_manager
load_dotenv()
import os
host = os.getenv('MCP_HOST', '127.0.0.1')
port = int(os.getenv('MCP_PORT', 9096))
mcp = FastMCP("Exam-Bot")


def discord_message_url(guild_id, channel_id, message_id):
    return f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}"


@mcp.tool()
def get_context(query: str, channel_id: str, author: Optional[str] = None) -> dict:
    """Search documents uploaded in this Discord channel. Use a question or topic as the query."""
    chunks = vector_manager.search_similar_chunks(query, channel_id=channel_id, author=author)
    matches = []
    for chunk in chunks:
        metadata = chunk["metadata"]
        matches.append({
            "source_url": discord_message_url(metadata.get("guild_id"), channel_id, metadata["message_id"]),
            "attachment_id": metadata["attachment_id"],
            "filename": metadata["filename"],
            "chunk_index": metadata["chunk_index"],
            "content": chunk["content"],
        })
    return {"matches": matches}


@mcp.tool()
def web_search(query: str) -> str:
    """
    Search the web for current information using Perplexity AI.
    
    Arguments:
        query: The search query or question to look up on the internet
    
    Returns:
        Web search results with current information and sources
    """
    print(f"Searching web for: {query}")
    
    result = search_web_perplexity(query)
    
    if result["success"]:
        print(f"Web search successful for: {query}")
        return result["content"]
    else:
        error_msg = f"Web search failed: {result['error']}"
        print(error_msg)
        return error_msg


@mcp.tool()
async def search_chats(
    keywords: list[str], channel_id: str, exclude_message_id: Optional[str] = None
) -> dict:
    """Find past discussions and decisions in this Discord channel. Use distinctive names, IDs, or terms as keywords."""
    messages = db_manager.get_chats(keywords, channel_id, exclude_message_id=exclude_message_id)
    return {
        "matches": [
            {
                "source_url": discord_message_url(message["guild_id"], channel_id, message["message_id"]),
                "message_id": message["message_id"],
                "author": message["author"],
                "timestamp": message["timestamp"].isoformat(),
                "content": message["content"],
            }
            for message in messages
        ]
    }


if __name__ == "__main__":
    print("🚀 Starting MCP server...")
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
        log_level="info",
    )
