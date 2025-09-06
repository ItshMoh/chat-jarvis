import mysql.connector
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

class TiDBManager:
    def __init__(self):
        self.connection = None
        self.connect()
    


    def connect(self):
        """Establish connection to TiDB database using connection URL"""
        try:
            connection_url = os.getenv('TIDB_CONNECTION_URL')
            
            if not connection_url:
                raise Exception("TIDB_CONNECTION_URL not found in environment variables")
            
            parsed_url = urlparse(connection_url)
            
            host = parsed_url.hostname
            port = parsed_url.port or 4000
            user = parsed_url.username
            password = parsed_url.password
            database = parsed_url.path.lstrip('/') if parsed_url.path else ''
            
            self.connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                ssl_ca=os.getenv('TIDB_SSL_CA') if os.getenv('TIDB_SSL_CA') else None,
                ssl_verify_cert=True if os.getenv('TIDB_SSL_CA') else False,
                ssl_verify_identity=True if os.getenv('TIDB_SSL_CA') else False,
                autocommit=True
            )
            print("Connected to TiDB successfully!")
            self.create_database_and_table()
        except Exception as e:
            print(f"Error connecting to TiDB: {e}")
    def create_database_and_table(self):
        """Create database and messages table if they don't exist"""
        try:
            cursor = self.connection.cursor()
            
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS chatJarvis")
            cursor.execute("USE chatJarvis")
            
            # Create table
            create_table_query = """
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id VARCHAR(20) UNIQUE NOT NULL,
                channel_id VARCHAR(20) NOT NULL,
                guild_id VARCHAR(20),
                author VARCHAR(255) NOT NULL,
                content TEXT,
                timestamp DATETIME NOT NULL,
                edited_timestamp DATETIME NULL,
                type INT DEFAULT 0,
                embeds JSON NULL,
                attachments JSON NULL,
                mentions JSON NULL,
                referenced_message_id VARCHAR(20) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_channel_id (channel_id),
                INDEX idx_guild_id (guild_id),
                INDEX idx_timestamp (timestamp)
            )
            """
            cursor.execute(create_table_query)
            cursor.close()
            print("Database and messages table created/verified successfully!")
        except Exception as e:
            print(f"Error creating database and table: {e}")
    
    def add_message(self, message_data):
        """Add a message to the database"""
        insert_query = """
        INSERT INTO messages 
        (message_id, channel_id, guild_id, author, content, timestamp, 
         edited_timestamp, type, embeds, attachments, mentions, referenced_message_id)
        VALUES (%(message_id)s, %(channel_id)s, %(guild_id)s, %(author)s, 
                %(content)s, %(timestamp)s, %(edited_timestamp)s, %(type)s, 
                %(embeds)s, %(attachments)s, %(mentions)s, %(referenced_message_id)s)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_query, message_data)
            cursor.close()
            print(f"Message added successfully: {message_data['message_id']}")
        except Exception as e:
            print(f"Error adding message: {e}")
    
    def get_chat_history(self, channel_id, limit=20):
        """Fetch chat history for a specific channel"""
        select_query = """
        SELECT author, content, type, referenced_message_id, timestamp
        FROM messages 
        WHERE channel_id = %s 
        ORDER BY timestamp DESC 
        LIMIT %s
        """
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(select_query, (channel_id, limit))
            results = cursor.fetchall()
            cursor.close()
            # Reverse to get chronological order (oldest first)
            return list(reversed(results))
        except Exception as e:
            print(f"Error fetching chat history: {e}")
            return []
    
    def get_referenced_message(self, message_id):
        """Get referenced message content for replies"""
        select_query = """
        SELECT author, content FROM messages WHERE message_id = %s
        """
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(select_query, (message_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            print(f"Error fetching referenced message: {e}")
            return None
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed.")


db_manager = TiDBManager()