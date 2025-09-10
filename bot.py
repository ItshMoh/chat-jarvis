from tidb import db_manager
import json
import asyncio
from filehandler import file_handler
from vectors import vector_manager

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

    async def store_attachment(self, message):
        """Store attachments and process them for vector storage"""
        if not message.attachments:
            return
        
        for attachment in message.attachments:
            try:
                # Check if file is supported
                if not file_handler.is_supported_file(attachment.filename, attachment.content_type):
                    continue
                
                # Prepare attachment data
                attachment_data = {
                    'attachment_id': str(attachment.id),
                    'message_id': str(message.id),
                    'channel_id': str(message.channel.id),
                    'guild_id': str(message.guild.id) if message.guild else None,
                    'author': str(message.author),
                    'filename': attachment.filename,
                    'title': None,
                    'description': None,
                    'content_type': attachment.content_type,
                    'size': attachment.size,
                    'url': attachment.url,
                    'proxy_url': attachment.proxy_url,
                    'timestamp': message.created_at
                }
                
                # Extract text content from attachment
                text_content = await file_handler.process_attachment({
                    'filename': attachment.filename,
                    'url': attachment.url,
                    'content_type': attachment.content_type
                })
                
                if text_content:
                    # Store document chunks in vector database
                    success = vector_manager.store_document_chunks(text_content, attachment_data)
                    
                    if success:
                        # Store attachment metadata in database
                        attachment_data['text_content'] = None  # Don't store raw text in DB
                        db_manager.add_attachment(attachment_data)
                        print(f"Successfully processed attachment: {attachment.filename}")
                    else:
                        print(f"Failed to store chunks for: {attachment.filename}")
                else:
                    print(f"Failed to extract text from: {attachment.filename}")
                    
            except Exception as e:
                print(f"Error processing attachment {attachment.filename}: {e}")     


botManager = BotMessage()