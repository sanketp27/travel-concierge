import os
import json
import datetime
import tempfile
import sqlite3
import time
from typing import Any, Optional

# LangChain imports - using new module paths
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.messages import HumanMessage , AIMessage

class HumanMessage:
    def __init__(self, content):
        self.content = content
        self.type = "human"

class AIMessage:
    def __init__(self, content):
        self.content = content
        self.type = "ai"

class SessionMessages:
    def __init__(self, cache, cache_key, session_id):
        self.cache = cache
        self.cache_key = cache_key
        self.session_id = session_id
        
    @property
    def messages(self):
        cached_messages = self.cache.get(self.cache_key, self.session_id)
        if not cached_messages:
            return []

        reconstructed_messages = []
        for msg in cached_messages:
            if msg["type"] == "human":
                reconstructed_messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                reconstructed_messages.append(AIMessage(content=msg["content"]))

        return reconstructed_messages
        
    def add_message(self, message):
        current_messages = self.messages
        current_messages.append(message)

        # Serialize messages for storage
        serialized_messages = []
        for msg in current_messages:
            if isinstance(msg, HumanMessage):
                serialized_messages.append({"type": "human", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serialized_messages.append({"type": "ai", "content": msg.content})

        self.cache.set(self.cache_key, serialized_messages, self.session_id)

    def add_user_message(self, message):
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message):
        self.add_message(AIMessage(content=message))

    def get_chat_message_history(self):
        """Return a proper ChatMessageHistory instance with the current messages."""
        history = ChatMessageHistory()
        
        cached_messages = self.cache.get(self.cache_key, self.session_id) or []

        for msg in cached_messages:
            if msg["type"] == "human":
                history.add_user_message(msg["content"])
            elif msg["type"] == "ai":
                history.add_ai_message(msg["content"])

        return history
    
    def get_message_dicts(self):
        """Convert message objects to dictionaries for ChatMessageHistory."""
        message_dicts = []
        for msg in self.messages:
            if isinstance(msg, HumanMessage):
                message_dicts.append({"type": "human", "content": msg.content})
            elif isinstance(msg, AIMessage):
                message_dicts.append({"type": "ai", "content": msg.content})
        return message_dicts
    
    def clear(self):
        """Clear all messages in the current session."""
        self.cache.set(self.cache_key, [], self.session_id)
    
class SQLCache:
    def __init__(self, session_id, context, table_name: str = "cache"):
        self.table_name = table_name
        self.org_table_name = "org_data"
        self.ssid = session_id
        self.context = context
        self.cache_key = str(session_id + context)
        self.database_path = self._get_database_path()
        self._init_db()

    def _get_database_path(self):
        temp_dir = tempfile.gettempdir()
        cache_db_filename = f"{self.ssid}_cache.db"
        cache_db_path = os.path.join(temp_dir, cache_db_filename)
        print(f"cache_db_path: {cache_db_path}")
        return cache_db_path

    def _init_db(self):
        """Initialize the SQLite database with a session-aware cache table."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create table with session_id column
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                key TEXT,
                value TEXT,
                session_id TEXT,
                expires_at REAL,
                PRIMARY KEY (key, session_id)
            )
        """)
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.org_table_name} (
                key TEXT,
                value TEXT,
                session_id TEXT,
                expires_at REAL,
                PRIMARY KEY (key, session_id)
            )
        """)
        
        conn.commit()
        conn.close()

    def set(self, key: str, value: Any, session_id: str, ttl: Optional[int] = None):
        """Set a value in the cache for a specific session."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Convert value to JSON string for storage
        serialized_value = json.dumps(value)
        
        # Calculate expiration time if TTL is provided
        expires_at = time.time() + ttl if ttl else None
        
        # Insert or replace the value
        cursor.execute(f"""
            INSERT OR REPLACE INTO {self.table_name} (key, value, session_id, expires_at)
            VALUES (?, ?, ?, ?)
        """, (key, serialized_value, session_id, expires_at))
        
        conn.commit()
        conn.close()
        
    def get(self, key: str, session_id: str, default: Any = None) -> Any:
        """Get a value from the cache for a specific session."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Query for the value with session_id
        cursor.execute(f"""
            SELECT value, expires_at FROM {self.table_name}
            WHERE key = ? AND session_id = ?
        """, (key, session_id))
        
        result = cursor.fetchone()
        conn.close()
        
        # Return default if no result found
        if not result:
            return default
            
        value, expires_at = result
        
        # Check if the value has expired
        if expires_at is not None and time.time() > expires_at:
            self.delete(key, session_id)
            return default
            
        # Deserialize the value from JSON
        return json.loads(value)
    
    
    def set_org_data(self, key: str, value: Any, session_id: str, ttl: Optional[int] = None):
        """Set a value in the cache for a specific session."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Convert value to JSON string for storage
        serialized_value = json.dumps(value)
        
        # Calculate expiration time if TTL is provided
        expires_at = time.time() + ttl if ttl else None
        
        # Insert or replace the value
        cursor.execute(f"""
            INSERT OR REPLACE INTO {self.org_table_name} (key, value, session_id, expires_at)
            VALUES (?, ?, ?, ?)
        """, (key, serialized_value, session_id, expires_at))
        
        conn.commit()
        conn.close()
        
    def get_org_data(self, key: str, session_id: str, default: Any = None) -> Any:
        """Get a value from the cache for a specific session."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
     
        cursor.execute(f"""
            SELECT value, expires_at FROM {self.org_table_name}
            WHERE key = ? AND session_id = ?
        """, (key, session_id))
        
        result = cursor.fetchone()
        conn.close()
        
        # Return default if no result found
        if not result:
            return default
            
        value, expires_at = result
        
        # Check if the value has expired
        if expires_at is not None and time.time() > expires_at:
            self.delete(key, session_id)
            return default
            
        return json.loads(value)
    
    def delete(self, key: str, session_id: str):
        """Delete a value from the cache for a specific session."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            DELETE FROM {self.table_name}
            WHERE key = ? AND session_id = ?
        """, (key, session_id))
        
        conn.commit()
        conn.close()
    
    def clear_session(self, session_id: str):
        """Clear all cache entries for a specific session."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            DELETE FROM {self.table_name}
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
    
    def clear_expired(self):
        """Clear all expired cache entries."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            DELETE FROM {self.table_name}
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (time.time(),))
        
        conn.commit()
        conn.close()
    
    def get_session_messages(self, session_id: str) -> SessionMessages:
        """Return a SessionMessages object for the given cache key and session."""
        return SessionMessages(self, self.cache_key, session_id)
    
