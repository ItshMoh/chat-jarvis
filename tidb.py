import mysql.connector
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

CHAT_DATABASE = "chatJarvis"


class TiDBManager:
    def __init__(self, connection=None):
        self.connection = connection
        if connection is None:
            self.connect()

    @staticmethod
    def open_connection(database=None):
        connection_url = os.getenv('TIDB_CONNECTION_URL')
        if not connection_url:
            raise ValueError("TIDB_CONNECTION_URL not found in environment variables")

        parsed_url = urlparse(connection_url)
        ssl_ca = os.getenv('TIDB_SSL_CA') or None
        return mysql.connector.connect(
            host=parsed_url.hostname,
            port=parsed_url.port or 4000,
            user=parsed_url.username,
            password=parsed_url.password,
            database=database if database is not None else parsed_url.path.lstrip('/'),
            ssl_ca=ssl_ca,
            ssl_verify_cert=bool(ssl_ca),
            ssl_verify_identity=bool(ssl_ca),
            autocommit=True,
            connection_timeout=10,
        )

    @classmethod
    @contextmanager
    def chat_session(cls):
        """Give each background job or search its own database connection."""
        with cls.open_connection(database=CHAT_DATABASE) as connection:
            yield cls(connection)

    def connect(self):
        """Establish connection to TiDB database using connection URL"""
        try:
            self.connection = self.open_connection()
            print("Connected to TiDB successfully!")
            self.create_database_and_table()
        except Exception as e:
            print(f"Error connecting to TiDB: {e}")
    def create_database_and_table(self):
        """Create database and messages table if they don't exist"""
        try:
            cursor = self.connection.cursor()
            
            # Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{CHAT_DATABASE}`")
            cursor.execute(f"USE `{CHAT_DATABASE}`")
            
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
            INDEX idx_timestamp (timestamp),
            FULLTEXT INDEX (content) WITH PARSER MULTILINGUAL
        )
            """
            cursor.execute(create_table_query)

            create_attachments_table_query = """
            CREATE TABLE IF NOT EXISTS attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                attachment_id VARCHAR(64) NOT NULL,
                message_id VARCHAR(64) NOT NULL,
                channel_id VARCHAR(64) NOT NULL,
                guild_id VARCHAR(64),
                author VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                title VARCHAR(255) NULL,
                description TEXT NULL,
                content_type TEXT NULL,
                size INT NOT NULL,
                url TEXT NOT NULL,
                proxy_url TEXT NOT NULL,
                text_content LONGTEXT NULL,
                vector_embedding JSON NULL,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_message_id (message_id),
                INDEX idx_channel_id (channel_id),
                INDEX idx_guild_id (guild_id),
                INDEX idx_author (author),
                INDEX idx_timestamp (timestamp),
                INDEX idx_content_type (content_type(255))
            )
            """
            cursor.execute(create_attachments_table_query)
            cursor.close()
            print("Database and tables (messages, attachments) created/verified successfully!")
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
    
    def add_attachment(self, attachment_data):
        """Add an attachment to the database"""
        insert_query = """
        INSERT INTO attachments 
        (attachment_id, message_id, channel_id, guild_id, author, filename, 
        title, description, content_type, size, url, proxy_url, text_content, 
        vector_embedding, timestamp)
        VALUES (%(attachment_id)s, %(message_id)s, %(channel_id)s, %(guild_id)s, 
                %(author)s, %(filename)s, %(title)s, %(description)s, %(content_type)s, 
                %(size)s, %(url)s, %(proxy_url)s, %(text_content)s, %(vector_embedding)s, 
                %(timestamp)s)
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_query, attachment_data)
            cursor.close()
            print(f"Attachment added successfully: {attachment_data['attachment_id']}")
        except Exception as e:
            print(f"Error adding attachment: {e}")
    def get_chat_history(self, channel_id, limit=20, *, exclude_message_id=None):
        """Fetch chat history for a specific channel"""
        select_query = """
        SELECT m.author, m.content, m.type, m.referenced_message_id, m.timestamp,
               reply.author AS reply_author, reply.content AS reply_content
        FROM messages AS m
        LEFT JOIN messages AS reply ON reply.message_id = m.referenced_message_id
                                    AND reply.channel_id = m.channel_id
        WHERE m.channel_id = %s
          AND (%s IS NULL OR m.message_id <> %s)
          AND m.content <> ''
        ORDER BY m.timestamp DESC, m.id DESC
        LIMIT %s
        """
        
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_query, (channel_id, exclude_message_id, exclude_message_id, limit))
                results = cursor.fetchall()
            # Reverse to get chronological order (oldest first)
            return list(reversed(results))
        except Exception as e:
            print(f"Error fetching chat history: {e}")
            return []
    
    def get_chats(self, keywords, channel_id, *, exclude_message_id=None, limit=5):
        """Search all stored messages in one Discord channel."""
        if not channel_id:
            raise ValueError("A channel ID is required for chat search")
        query = " ".join(dict.fromkeys(word.strip() for word in keywords if word.strip()))
        if not query:
            return []

        search_query = """
        SELECT message_id, guild_id, author, content, timestamp
        FROM messages
        WHERE channel_id = %s
          AND (%s IS NULL OR message_id <> %s)
          AND fts_match_word(%s, content)
        ORDER BY fts_match_word(%s, content) DESC, timestamp DESC, id DESC
        LIMIT %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                search_query, (channel_id, exclude_message_id, exclude_message_id, query, query, limit)
            )
            return cursor.fetchall()
    
    def create_chat_embedding_table(self):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_message_embeddings (
                    message_id VARCHAR(20) NOT NULL,
                    model_key VARCHAR(255) NOT NULL,
                    channel_id VARCHAR(20) NOT NULL,
                    embedding VECTOR NOT NULL,
                    PRIMARY KEY (message_id, model_key),
                    INDEX idx_chat_embedding_scope (channel_id, model_key)
                )
            """)

    def get_unindexed_chats(self, model_key, *, after_id, limit):
        """Read a batch from the transcript, using committed embeddings as progress."""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT m.id, m.message_id, m.channel_id, m.content,
                       reply.content AS reply_content
                FROM messages AS m
                LEFT JOIN chat_message_embeddings AS e
                    ON e.message_id = m.message_id AND e.model_key = %s
                LEFT JOIN messages AS reply
                    ON reply.message_id = m.referenced_message_id AND reply.channel_id = m.channel_id
                WHERE m.id > %s AND e.message_id IS NULL AND m.content <> ''
                ORDER BY m.id
                LIMIT %s
            """, (model_key, after_id, limit))
            return cursor.fetchall()

    def store_chat_embeddings(self, rows):
        with self.connection.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO chat_message_embeddings (message_id, model_key, channel_id, embedding)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE embedding = VALUES(embedding), channel_id = VALUES(channel_id)
            """, rows)

    def get_semantic_chat_ids(self, embedding, model_key, channel_id, *, exclude_message_id=None, limit=20):
        """Rank embeddings in the requested channel before applying the result limit."""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.message_id
                FROM chat_message_embeddings AS e
                JOIN messages AS m ON m.message_id = e.message_id AND m.channel_id = e.channel_id
                WHERE e.channel_id = %s AND e.model_key = %s
                    AND (%s IS NULL OR e.message_id <> %s)
                    AND m.content <> ''
                ORDER BY VEC_COSINE_DISTANCE(e.embedding, VEC_FROM_TEXT(%s)), e.message_id
                LIMIT %s
            """, (channel_id, model_key, exclude_message_id, exclude_message_id, embedding, limit))
            return [message_id for (message_id,) in cursor.fetchall()]

    def get_chat_search_messages(self, message_ids, channel_id, *, exclude_message_id=None):
        """Fetch ranked hits and any same-channel reply parents from the transcript."""
        if not message_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(message_ids))
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(f"""
                SELECT m.message_id, m.guild_id, m.author, m.content, m.timestamp,
                       reply.message_id AS reply_message_id, reply.author AS reply_author,
                       reply.content AS reply_content, reply.timestamp AS reply_timestamp
                FROM messages AS m
                LEFT JOIN messages AS reply
                    ON reply.message_id = m.referenced_message_id AND reply.channel_id = m.channel_id
                    AND (%s IS NULL OR reply.message_id <> %s)
                WHERE m.channel_id = %s AND m.message_id IN ({placeholders})
                    AND (%s IS NULL OR m.message_id <> %s)
                    AND m.content <> ''
            """, (
                exclude_message_id, exclude_message_id, channel_id, *message_ids,
                exclude_message_id, exclude_message_id,
            ))
            return {message["message_id"]: message for message in cursor.fetchall()}

    def get_referenced_message(self, message_id, channel_id):
        """Get referenced message content for replies"""
        select_query = """
        SELECT author, content FROM messages WHERE message_id = %s AND channel_id = %s
        """
        
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(select_query, (message_id, channel_id))
                return cursor.fetchone()
        except Exception as e:
            print(f"Error fetching referenced message: {e}")
            return None
    
    def delete_table(self, table_name: str, confirm: bool = False) -> bool:
        """
        Delete a table from the TiDB database
        
        Args:
            table_name: Name of the table to delete
            confirm: Safety confirmation flag
            
        Returns:
            True if successful, False otherwise
        """
        if not confirm:
            print(f"WARNING: This will permanently delete the table '{table_name}'!")
            print("To proceed, call this method with confirm=True")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Check if table exists first
            check_query = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = %s
            """
            cursor.execute(check_query, (table_name,))
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print(f"Table '{table_name}' does not exist.")
                cursor.close()
                return False
            
            # Delete the table
            drop_query = f"DROP TABLE {table_name}"
            cursor.execute(drop_query)
            cursor.close()
            
            print(f"Table '{table_name}' deleted successfully!")
            return True
            
        except Exception as e:
            print(f"Error deleting table '{table_name}': {e}")
            return False
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed.")


db_manager = TiDBManager()
