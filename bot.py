from tidb import db_manager
import json

class BotMessage:

    def __init_(self):
        return 
    
    async def store_message(self,message):
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

    async def store_bot_message(self,bot_message, referenced_message_id):
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


botManager = BotMessage()