import asyncio
import os
from contextlib import asynccontextmanager, suppress
from typing import Optional

from fastmcp import FastMCP
from dotenv import load_dotenv

from chat_search import maintain_chat_index, search_chat_history
from netsearch import search_web_perplexity
from vectors import vector_manager

load_dotenv()
host = os.getenv('MCP_HOST', '127.0.0.1')
port = int(os.getenv('MCP_PORT', 9096))


@asynccontextmanager
async def lifespan(server):
    indexer = asyncio.create_task(maintain_chat_index())
    try:
        yield {}
    finally:
        indexer.cancel()
        with suppress(asyncio.CancelledError):
            await indexer


mcp = FastMCP("Exam-Bot", lifespan=lifespan)


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
    keywords: list[str], channel_id: str, exclude_message_id: Optional[str] = None,
    query: Optional[str] = None,
) -> dict:
    """Find past discussions in this Discord channel using meaning and keywords.

    Use the question or topic as query and supply distinctive names, IDs, or terms
    as keywords. Use an empty keyword list for a query without distinctive terms.
    """
    messages, unavailable = await asyncio.to_thread(
        search_chat_history, keywords, channel_id, query=query, exclude_message_id=exclude_message_id,
    )
    matches = []
    for message in messages:
        guild_id = message["guild_id"]
        match = {
            "source_url": discord_message_url(guild_id, channel_id, message["message_id"]),
            "message_id": message["message_id"],
            "author": message["author"],
            "timestamp": message["timestamp"].isoformat(),
            "content": message["content"],
        }
        if message["reply_message_id"]:
            match["reply_to"] = {
                "source_url": discord_message_url(guild_id, channel_id, message["reply_message_id"]),
                "author": message["reply_author"],
                "timestamp": message["reply_timestamp"].isoformat(),
                "content": message["reply_content"],
            }
        matches.append(match)

    result = {"matches": matches}
    if unavailable:
        result["unavailable"] = unavailable
    return result


if __name__ == "__main__":
    print("🚀 Starting MCP server...")
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
        log_level="info",
    )
