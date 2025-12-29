"""
Configuration file for C2 Server and Client
All configurable parameters are centralized here to avoid hardcoded values
"""

import os

# Server Configuration
SERVER_HOST = os.getenv("C2_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("C2_SERVER_PORT", "8888"))

# Client Configuration
CLIENT_SERVER_HOST = os.getenv("C2_CLIENT_SERVER_HOST", "127.0.0.1")
CLIENT_SERVER_PORT = int(os.getenv("C2_CLIENT_SERVER_PORT", "8888"))
CLIENT_RECONNECT_INTERVAL = int(os.getenv("C2_CLIENT_RECONNECT_INTERVAL", "5"))

# Encryption Configuration
# Pre-shared key for AES-256-GCM (must be 32 bytes)
# In production, this should be securely distributed
ENCRYPTION_PSK = os.getenv("C2_ENCRYPTION_PSK", "this_is_a_32_byte_psk_key_123").encode()[:32].ljust(32, b'0')

# Protocol Configuration
MESSAGE_LENGTH_PREFIX_SIZE = 4  # 4 bytes for message length header
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB max message size

# Heartbeat Configuration
HEARTBEAT_INTERVAL = int(os.getenv("C2_HEARTBEAT_INTERVAL", "30"))  # seconds
HEARTBEAT_TIMEOUT = int(os.getenv("C2_HEARTBEAT_TIMEOUT", "90"))  # seconds

# Database Configuration
DB_HOST = os.getenv("C2_DB_HOST", "localhost")
DB_PORT = int(os.getenv("C2_DB_PORT", "5432"))
DB_NAME = os.getenv("C2_DB_NAME", "c2_logs")
DB_USER = os.getenv("C2_DB_USER", "c2admin")
DB_PASSWORD = os.getenv("C2_DB_PASSWORD", "c2password")

# Logging Configuration
LOG_LEVEL = os.getenv("C2_LOG_LEVEL", "INFO")

# CLI Display Configuration
CLI_TABLE_WIDTH_NARROW = 50  # Width for narrow tables (status)
CLI_TABLE_WIDTH_STANDARD = 80  # Width for standard tables (client list)
CLI_TABLE_WIDTH_WIDE = 100  # Width for wide tables (database queries)
CLI_CLIENT_ID_WIDTH = 38  # UUID string width
CLI_ADDRESS_WIDTH = 22  # IP:port string width
CLI_STATUS_WIDTH = 10  # Status field width
CLI_TIMESTAMP_WIDTH = 20  # Timestamp field width
CLI_EVENT_TYPE_WIDTH = 20  # Event type field width
CLI_COMMAND_TYPE_WIDTH = 10  # Command type field width
CLI_COMMAND_WIDTH = 30  # Command text preview width
CLI_RESULT_WIDTH = 30  # Result text preview width
CLI_SUCCESS_WIDTH = 8  # Success boolean width
CLI_DETAILS_WIDTH = 20  # Details field width
CLI_DEFAULT_DB_LIMIT = 10  # Default number of database records to show

# Command Execution Configuration
COMMAND_TIMEOUT = 30.0  # Timeout for bash command execution (seconds)
COMMAND_QUEUE_TIMEOUT = 1.0  # Timeout for command queue polling (seconds)

# Database Connection Pool Configuration
DB_POOL_MIN_CONNECTIONS = 1  # Minimum connections in pool
DB_POOL_MAX_CONNECTIONS = 10  # Maximum connections in pool
