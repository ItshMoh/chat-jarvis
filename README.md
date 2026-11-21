# Discord Jarvis Bot 🤖

A powerful Discord bot that combines chat capabilities with document processing, vector search, and web search functionality. Jarvis can understand context from uploaded documents, search through chat history, and provide up-to-date information from the web.

## ✨ Features
- 💬 Conversational AI: Powered by OpenAI GPT or Open Source models with chat history context
- 📄 Document Processing: Automatically processes **PDF**, **DOCX**, and **TXT** file uploads
- 🔍 Vector Search: Semantic search through uploaded documents using **TiDB Vector Search**
- 🌐 Web Search: Real-time web search capabilities via **Perplexity AI**
- 📊 Hybrid Chat Search: Find past chats by keyword or meaning
- 🛠️ Tool Integration: Extensible tool system using **FastMCP**

## 🎥 Demo Video
https://www.loom.com/share/d117f2aaf329475999278ad3859c4460?sid=cde0add4-b238-4328-ad8b-6137a88db187

## 🏗️ Architecture

The bot uses several key components:

- Discord Bot: Main interface for user interactions
- TiDB stores the chat transcript, attachment metadata, and embeddings for chats and uploaded documents.
- LLM Integration: OpenAI API for conversational responses
- MCP Tools: Modular tool system for extensible functionality


## 🚀 Quick Start

Prerequisites

- Python 3.10+
- A TiDB instance with native vector support and full-text search for hybrid chat recall
- Discord Bot Token
- OpenAI API Key
- Perplexity AI API Key (optional, for web search)

## Installation

1. Clone the repository

```bash
git clone https://github.com/ItshMoh/chat-jarvis
cd chat-jarvis
```
2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables
Create a .env file in the root directory: 
```bash
# Discord Configuration
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   
   # TiDB Configuration
   TIDB_CONNECTION_URL=mysql+pymysql://username:password@host:port/chatJarvis
   TIDB_SSL_CA=path/to/ca-cert.pem  # Optional, for SSL
   
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   API_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o
   TEMPERATURE=0.7
   MAX_TOKENS=1500
   
   # Perplexity AI (Optional - for web search)
   PPLX_API_KEY=your_perplexity_api_key_here
   
   # MCP Server Configuration
   MCP_HOST=127.0.0.1
   MCP_PORT=9096
   ```

### Setting Up TiDB Cloud

1. Choose an instance that supports the `VECTOR` type and TiDB full-text search. Check availability for your plan and region. [TiDB vector types](https://docs.pingcap.com/tidb/dev/vector-search-data-types/) · [TiDB full-text search](https://docs.pingcap.com/ai/vector-search-full-text-search-sql/#get-started)
2. Create the `chatJarvis` database if needed and use it in `TIDB_CONNECTION_URL` in your `.env` file.
3. Use a database account that can read, write, and create tables in `chatJarvis`. The MCP server creates the chat embedding table on startup.

### Setting Up Discord Bot

- Go to Discord Developer Portal at [discord.com/developers/applications](https://discord.com/developers/applications)
- Create New Application and give it a name
- Go to **Bot section** and create a bot
- Copy the token and add it to your .env file
- Set permissions: **Send Messages, Read Message History, Attach Files**
- Invite bot to your server using the **OAuth2 URL generator**

## 🎮 Usage

### Starting the Bot

1. Start the **MCP server** (in one terminal):

```bash
python tools.py
```

2. Start the Discord bot (in another terminal):

```bash
python main.py
```

### Bot Commands

- /bot <your question> - Ask Jarvis anything
```
/bot What is machine learning?
/bot Summarize the document I just uploaded
/bot What's the latest news about AI?
```

### File Upload Support

Simply upload supported files (PDF, DOCX, TXT) to any channel where Jarvis is present. The bot will automatically:

- Extract text content
- Create semantic chunks
- Store in vector database
- Make content searchable


## 🧠 How It Works

Document Processing Pipeline

- File Upload Detection → Automatic processing of attachments
- Text Extraction → Support for PDF, DOCX, TXT formats
- Chunking → Split into manageable pieces using RecursiveCharacterTextSplitter
- Embedding Generation → Create vector embeddings using sentence-transformers
- Vector Storage → Store in TiDB Vector for semantic search

## Conversation memory

TiDB stores the messages Jarvis receives. For each reply, Jarvis takes up to 50 recent messages from the current Discord channel and fits the newest messages into an 8 KB prompt budget. Older messages are available through hybrid chat search. The model can make follow-up tool calls to refine a query or look up both a discussion and a document.

The planned rolling thread summary has an 800-token cap.

| Tool | Model input | Sources |
| --- | --- | --- |
| `search_chats` | Natural-language query and a list of distinctive keywords. An empty keyword list runs semantic search alone. | Keyword and semantic matches combined by message ID, with authors, timestamps, and message links |
| `get_context` | Search query and optional author | Indexed uploads ranked by vector similarity, with filenames, chunk numbers, and upload message links |
| `web_search` | Public search query | Current web information from Perplexity |

Jarvis supplies the Discord channel ID to both memory tools. A channel, thread, or DM searches its own history and uploads. In servers, the requester needs Discord's Read Message History permission. Run the trusted MCP backend on the default loopback address for a local deployment.

The keyword branch uses the full-text index on `messages.content`. For an older table created without the index, follow the [TiDB instructions for adding a full-text index](https://docs.pingcap.com/ai/vector-search-full-text-search-sql/#create-a-full-text-index).

### Hybrid search rollout

Restart the MCP server and Discord bot after upgrading. On startup, the MCP server creates `chat_message_embeddings` and backfills messages already stored in TiDB in batches. It resumes from the embeddings already stored after a restart. After catching up, it checks for new messages about every 30 seconds. Keyword search is available during the backfill.

When Jarvis calls `search_chats`, the tool considers up to 20 results per method and merges their rankings with reciprocal rank fusion. It returns up to five primary matches. Each match can include the same-channel message it replied to, with its own source link. [TiDB hybrid search](https://docs.pingcap.com/ai/vector-search-hybrid-search-sql/)

### Verify chat and file recall

1. With the bot running, post `ATLAS-421 ships Thursday after QA signs off.` in a test channel. Add enough newer messages to push the decision out of the recent window and give the indexer time to process it.
2. Ask `/bot What was the decision on ATLAS-421?` to check keyword recall. Then ask `/bot When did we agree to go live, and what has to happen first?` to check paraphrased recall. Check that both answers link to the original message.
3. Repeat the request in a different channel to verify that Jarvis keeps the original discussion within its channel.
4. To check file retrieval, attach a document to `/bot What does the uploaded file say about [topic]?` and check for the link to the upload.

## 🔍 Troubleshooting

### Common Issues

1.  Bot not responding
  - Check if both tools.py and main.py are running
  - Verify Discord token and permissions
  - Check console for error messages

2. Database connection errors

- Verify TiDB connection URL format
- Check network connectivity
- Ensure database exists and is accessible

3. File processing failures

- Check if required libraries are installed (PyPDF2, python-docx)
- Verify file size limits (50MB max)
- Check file format support


4. Vector search not working

- Ensure TiDB Vector is enabled in your cluster
- Check embedding dimension compatibility
- Verify vector table creation

### Chat search misses older messages

- **Keyword misses.** Check that the original message is stored in TiDB and `messages.content` has a full-text index.
- **Paraphrase misses.** Check that `chat_message_embeddings` is filling during backfill. Look in the MCP server logs for `Chat embedding index could not advance` or `Chat semantic search failed` and check the database account's table permissions.
- **Scope.** Run the test in the Discord channel or thread where the original message was posted. In a server, the requester needs Read Message History permission there.
