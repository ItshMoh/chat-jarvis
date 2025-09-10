import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from llm import llmManager
import asyncio
from bot import botManager

load_dotenv()

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
    await botManager.store_message(message)
    if message.attachments:
        asyncio.create_task(botManager.store_attachment(message))

    # Check if message starts with /bot
    if message.content.startswith('/bot'):
        question = message.content[4:].strip()
        
        if not question:
            await message.channel.send("Please ask me something! Example: `/bot What is Python?`")
            return
        
        # Generate and send response
        response = await llmManager.reply_query(question, message)
        bot_message = await message.channel.send(response)
        
        # Store bot response in database
        await botManager.store_bot_message(bot_message, message.id)
    
    await bot.process_commands(message)


# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("Error: Please set DISCORD_BOT_TOKEN in your environment variables")
    else:
        bot.run(TOKEN)