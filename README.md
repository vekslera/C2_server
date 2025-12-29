# C2 Server - Command & Control System

A Python-based Command & Control (C2) server and demo client for cybersecurity training and testing.

## Architecture Overview

### Design Principles
- **Python 3.10+ with asyncio**: Fully asynchronous architecture for handling multiple concurrent clients
- **TCP Protocol**: Raw TCP sockets with custom length-prefixed message framing
- **Message Format**: JSON payloads with 4-byte length header (big-endian)
- **Encryption**: AES-256-GCM with pre-shared key (PSK)
- **Modular Design**: SOLID principles with clear separation of concerns

### System Components

```
┌─────────────────┐         ┌──────────────────┐
│   C2 Server     │◄────────┤   C2 Client      │
│   (Admin CLI)   │         │   (Demo Agent)   │
│                 │         │                   │
│  - Protocol     │         │  - Auto reconnect │
│  - Client Mgmt  │         │  - Heartbeat      │
│  - Command Exec │         │  - Cmd Queue      │
└────────┬────────┘         └───────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Logging DB)  │
└─────────────────┘
```

### Protocol Details

**Message Framing:**
```
[4-byte length][JSON payload]
```

**Message Types:**
- `welcome`: Server → Client (initial connection)
- `command`: Server → Client (execute command)
- `command_result`: Client → Server (execution result)
- `heartbeat`: Client → Server (keep-alive)
- `heartbeat_ack`: Server → Client (acknowledgment)

**Command Types:**
- `echo`: Simple echo test
- `kill`: Terminate client
- `bash`: Execute shell command (Step 4)

**Encryption (Step 2):**
- Algorithm: AES-256-GCM (Galois/Counter Mode)
- Key: 32-byte pre-shared key (PSK) from config
- Authenticated encryption prevents tampering
- Random 12-byte nonce per message
- Format: `[nonce][ciphertext+auth_tag]`

## Quick Start Guide

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Docker & Docker Compose (for Step 3 - database)

### Installation

**Install Dependencies:**
```bash
pip3 install -r requirements.txt
```

### Running the System - Step 1 Testing

#### Terminal 1 - Start the Server:
```bash
cd /home/alexv/C2_server
python3 server/main.py
```

You should see:
```
============================================================
C2 Server - Command & Control Server
============================================================
C2 Server started on 0.0.0.0:8888
C2 Server CLI - Type 'help' for commands
C2>
```

#### Terminal 2 - Start a Client:
```bash
cd /home/alexv/C2_server
python3 client/c2_client.py
```

You should see:
```
Connected to C2 Server. Client ID: abc-123-def-456...
```

### Manual Testing Instructions for Step 1

1. **Start the server** in Terminal 1
2. **Start 2-3 clients** in separate terminals (repeat the client command)
3. **List clients**: Type `list` in server CLI - verify all clients appear
4. **Test echo**: Type `echo <client_id> Hello World` - verify response appears
5. **Test kill**: Type `kill <client_id>` - verify client disconnects
6. **Exit server**: Type `exit` - verify graceful shutdown

### Server CLI Commands

Once the server is running, use these commands:

**List all connected clients:**
```
C2> list
```

**Send echo command:**
```
C2> echo <client_id> Hello World
```
Example:
```
C2> echo abc-123 Hello from C2 Server!
```

**Kill a client:**
```
C2> kill <client_id>
```

**Get detailed status:**
```
C2> status <client_id>
```

**Execute bash command (Step 4):**
```
C2> bash <client_id> ls -la
```

**Show help:**
```
C2> help
```

**Exit server:**
```
C2> exit
```

## Configuration

All configuration is centralized in [config.py](config.py). No hardcoded values. Key settings:

```python
# Server
SERVER_HOST = "0.0.0.0"      # Bind address
SERVER_PORT = 8888            # Listen port

# Client
CLIENT_SERVER_HOST = "127.0.0.1"  # Target server
CLIENT_SERVER_PORT = 8888          # Target port
CLIENT_RECONNECT_INTERVAL = 5      # Reconnection delay (seconds)

# Encryption (Step 2)
ENCRYPTION_PSK = "your-32-byte-key"  # Pre-shared key

# Heartbeat (Step 4)
HEARTBEAT_INTERVAL = 30       # Send heartbeat every 30s
HEARTBEAT_TIMEOUT = 90        # Consider dead after 90s

# Database (Step 3)
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "c2_logs"
DB_USER = "c2admin"
DB_PASSWORD = "c2password"
```

## Project Structure

```
C2_server/
├── server/
│   ├── __init__.py
│   ├── main.py           # Server entry point
│   ├── c2_server.py      # Core server logic
│   ├── cli.py            # Admin CLI interface
│   └── protocol.py       # Message framing & encryption
├── client/
│   ├── __init__.py
│   └── c2_client.py      # Demo client/agent
├── tests/
│   └── (test files)
├── config.py             # Centralized configuration
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Database setup (Step 3)
└── README.md            # This file
```

## Implementation Status

### ✅ Step 1 - Basic Connectivity (COMPLETED)
- [x] Server accepts multiple client connections
- [x] Client auto-connects to server with reconnection
- [x] CLI for admin commands
- [x] List connected clients with status
- [x] Echo command with response
- [x] Kill command

### ✅ Step 2 - Encryption (COMPLETED)
- [x] AES-256-GCM authenticated encryption implemented
- [x] Pre-shared key (PSK) configured
- [x] All communication encrypted
- [x] Encryption tests passing (5/5)

### 📋 Step 3 - Microservice Architecture
- [ ] PostgreSQL database setup
- [ ] Log all events to database
- [ ] Store commands and results

### 🚧 Step 4 - Advanced Functionality
- [x] Bash command execution (implemented)
- [x] Async command queue (implemented)
- [x] Heartbeat mechanism (implemented)
- [x] Async server (non-blocking)
- [ ] Load tested with many clients

### 📋 Step 5 - Testing
- [x] Protocol tests (5/5 passing)
- [x] Encryption tests (5/5 passing)
- [ ] Integration tests
- [ ] Scale tests

## Code Quality

### Architecture Principles Applied
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Inversion**: Database logger injected into server
- **No Hardcoded Values**: All config in config.py
- **Type Hints**: All functions have type annotations
- **Async Throughout**: Fully async/await pattern

### Code Citations
- Length-prefixed framing: Python asyncio documentation (https://docs.python.org/3/library/asyncio-stream.html)
- AES-GCM encryption: Cryptography library documentation (https://cryptography.io/en/latest/hazmat/primitives/aead/)
- Async subprocess: Python subprocess documentation (https://docs.python.org/3/library/subprocess.html)
- Non-blocking input: asyncio run_in_executor pattern (https://docs.python.org/3/library/asyncio-eventloop.html)

## Security Considerations
- **Pre-shared Key**: In production, use proper key exchange (ECDH)
- **Shell Execution**: `bash` command uses `shell=True` - validate inputs in production
- **Authentication**: No client authentication yet - add in production
- **Rate Limiting**: No rate limiting - add for production use

## Troubleshooting

**Client can't connect:**
- Check server is running: `netstat -ln | grep 8888`
- Check firewall rules
- Verify `CLIENT_SERVER_HOST` in config.py

**"Address already in use" error:**
- Another process is using port 8888
- Change port in config.py or kill existing process

**No response from client:**
- Check client logs for errors
- Verify client ID is correct (use `list` command)
- Ensure client is running