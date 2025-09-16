# Discord Jarvis Bot 🤖

A powerful Discord bot that combines chat capabilities with document processing, vector search, and web search functionality. Jarvis can understand context from uploaded documents, search through chat history, and provide up-to-date information from the web.

## ✨ Features
- 💬 Conversational AI: Powered by OpenAI GPT or Open Source models with chat history context
- 📄 Document Processing: Automatically processes **PDF**, **DOCX**, and **TXT** file uploads
- 🔍 Vector Search: Semantic search through uploaded documents using **TiDB Vector Search**
- 🌐 Web Search: Real-time web search capabilities via **Perplexity AI**
- 📊 Full-Text Search: Search through chat history using TiDB's full-text search
- 🛠️ Tool Integration: Extensible tool system using **FastMCP**

## 🎥 Demo Video
https://www.loom.com/share/d117f2aaf329475999278ad3859c4460?sid=cde0add4-b238-4328-ad8b-6137a88db187

## 🏗️ Architecture

The bot uses several key components:

- Discord Bot: Main interface for user interactions
- TiDB Database: Stores chat history and attachments with vector search capabilities
- Vector Store: Semantic search through document chunks
- LLM Integration: OpenAI API for conversational responses
- MCP Tools: Modular tool system for extensible functionality


## 🚀 Quick Start

Prerequisites

- Python 3.8+
- TiDB Cloud account (free tier available)
- Discord Bot Token
- OpenAI API Key
- Perplexity AI API Key (optional, for web search)

## Installation

1. Clone the repository

```bash
git clone https://github.com/ItshMoh/chat-jarvis
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
   TIDB_CONNECTION_URL=mysql+pymysql://username:password@host:port/database
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

- Create a TiDB Cloud account at tidbcloud.com
- Create a new cluster (Starter tier is free)
- Get connection details and update your .env file
- Enable Vector Search in your cluster settings

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

## Intelligent Response System

- Context Gathering → Retrieve chat history and relevant documents
- Tool Selection → Automatically choose appropriate tools (document search, web search, chat search)
- Response Generation → Generate contextual responses using OpenAI
- Memory Storage → Store conversations for future context

## 🛠️ Available Tools
These all tools are available to the bot with the help of MCP server.
1. get_context
Searches through uploaded documents for relevant information

- Input: Query string, optional channel_id, optional author
- Output: Relevant document chunks with metadata

2. web_search
Searches the web for current information using Perplexity AI

- Input: Search query
- Output: Current web information with sources

3. search_chats
Searches through chat history using full-text search

- Input: List of keywords
- Output: Relevant chat messages



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