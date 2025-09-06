import discord
from discord.ext import commands
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from tidb import db_manager
import openai
import requests


load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready and connected to {len(bot.guilds)} server(s)')

@bot.event
async def on_message(message):
    # Don't respond to bot's own messages
    if message.author == bot.user:
        return
    
    # Store all messages in database
    await store_message(message)
    
    # Check if message starts with /bot
    if message.content.startswith('/bot'):
        question = message.content[4:].strip()
        
        if not question:
            await message.channel.send("Please ask me something! Example: `/bot What is Python?`")
            return
        
        # Generate and send response
        response = await reply_query(question, message)
        bot_message = await message.channel.send(response)
        
        # Store bot response in database
        await store_bot_message(bot_message, message.id)
    
    await bot.process_commands(message)

async def store_message(message):
    """Store Discord message in database"""
    message_data = {
        'message_id': str(message.id),
        'channel_id': str(message.channel.id),
        'guild_id': str(message.guild.id) if message.guild else None,
        'author': str(message.author),
        'content': message.content,
        'timestamp': message.created_at,
        'edited_timestamp': message.edited_at,
        'type': message.type.value,
        'embeds': json.dumps([embed.to_dict() for embed in message.embeds]) if message.embeds else None,
        'attachments': json.dumps([{'filename': att.filename, 'url': att.url} for att in message.attachments]) if message.attachments else None,
        'mentions': json.dumps([str(user.id) for user in message.mentions]) if message.mentions else None,
        'referenced_message_id': str(message.reference.message_id) if message.reference else None
    }
    
    db_manager.add_message(message_data)

async def store_bot_message(bot_message, referenced_message_id):
    """Store bot response in database"""
    message_data = {
        'message_id': str(bot_message.id),
        'channel_id': str(bot_message.channel.id),
        'guild_id': str(bot_message.guild.id) if bot_message.guild else None,
        'author': 'bot',
        'content': bot_message.content,
        'timestamp': bot_message.created_at,
        'edited_timestamp': None,
        'type': 0,
        'embeds': None,
        'attachments': None,
        'mentions': None,
        'referenced_message_id': str(referenced_message_id)
    }
    
    db_manager.add_message(message_data)

async def reply_query(question, message):
    """Generate response using OpenAI with chat history context"""
    channel_id = str(message.channel.id)
    author = str(message.author)
    
    # Get chat history
    chat_history = db_manager.get_chat_history(channel_id, limit=10)
    
    # Build context for OpenAI
    messages = [
        {"role": "system", "content": "You are Jarvis, a helpful Discord bot. Respond conversationally based on the chat context. Don't give very long Answer try to answer it in less than 1500 words."}
    ]
    
    # Add chat history as context
    for chat in chat_history:
        if chat['author'] == 'bot':
            messages.append({"role": "assistant", "content": chat['content']})
        else:
            content = f"{chat['author']}: {chat['content']}"
            if chat['referenced_message_id']:
                ref_msg = db_manager.get_referenced_message(chat['referenced_message_id'])
                if ref_msg:
                    content = f"[Replying to {ref_msg['author']}: {ref_msg['content']}] {content}"
            messages.append({"role": "user", "content": content})
    
    # Add current question
    current_content = f"{author}: {question}"
    if message.reference:
        ref_msg = db_manager.get_referenced_message(str(message.reference.message_id))
        if ref_msg:
            current_content = f"[Replying to {ref_msg['author']}: {ref_msg['content']}] {current_content}"
    
    messages.append({"role": "user", "content": current_content})
    
    try:
        headers = {
            'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-4o',
            'messages': messages,
            'max_tokens': 500,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            result = response_data['choices'][0]['message']['content'].strip()
            print(f"OpenAI API response: {result} \n")
            return response_data['choices'][0]['message']['content'].strip()
        else:
            print(f"OpenAI API error: {response.status_code} - {response.text}")
            return "Sorry, I'm having trouble processing your request right now."

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "Sorry, I'm having trouble processing your request right now."

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("Error: Please set DISCORD_BOT_TOKEN in your environment variables")
    else:
        bot.run(TOKEN)