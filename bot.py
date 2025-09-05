import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready and connected to {len(bot.guilds)} server(s)')

@bot.event
async def on_message(message):
    # Don't respond to bot's own messages
    if message.author == bot.user:
        return
    
    # Check if message starts with /bot
    if message.content.startswith('/bot'):
        # Extract the question after /bot
        question = message.content[4:].strip()  # Remove '/bot' and whitespace
        
        if not question:
            await message.channel.send("Please ask me something! Example: `/bot What is Python?`")
            return
        
        # Process the question and generate response
        response = await generate_response(question)
        
        # Send the response
        await message.channel.send(response)
    
    # Process other commands
    await bot.process_commands(message)

async def generate_response(question):
    """
    Generate a response based on the question.
    You can customize this function to integrate with AI APIs,
    databases, or implement your own logic.
    """
    
    # Simple example responses - you can replace this with AI integration
    responses = {
        "hello": "Hello! How can I help you today?",
        "how are you": "I'm doing great! Thanks for asking.",
        "what is python": "Python is a high-level programming language known for its simplicity and versatility.",
        "help": "I'm here to help! Ask me anything using `/bot your question`",
    }
    
    question_lower = question.lower()
    
    # Check for keyword matches
    for key, response in responses.items():
        if key in question_lower:
            return response
    
    # Default response for unrecognized questions
    return f"I received your question: '{question}'. This is a basic response - you can enhance me with AI capabilities!"

# Optional: Add traditional Discord slash commands
@bot.command(name='ping')
async def ping(ctx):
    """Check if bot is responsive"""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='info')
async def info(ctx):
    """Get bot information"""
    embed = discord.Embed(
        title="Bot Information", 
        description="A custom Discord bot that responds to /bot commands",
        color=0x00ff00
    )
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Commands", value="Use `/bot <your question>` to ask me anything!", inline=False)
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_error(event, *args, **kwargs):
    print(f'An error occurred: {event}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    print(f'Command error: {error}')

# Run the bot
if __name__ == "__main__":
    # Get token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("Error: Please set DISCORD_BOT_TOKEN in your environment variables or .env file")
    else:
        bot.run(TOKEN)