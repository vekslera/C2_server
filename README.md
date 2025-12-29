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
- Docker & Docker Compose (recommended)
- **OR** Python 3.10+ and pip (for local development)

### Option 1: Docker Deployment (Recommended)

The easiest way to run the entire C2 infrastructure with database, server, and clients:

**Start all services:**
```bash
cd docker
docker-compose up --build
```

This will start:
- PostgreSQL database with initialized schema
- C2 server with admin CLI (attached to terminal)
- One C2 client (auto-connects to server)

**Scale to multiple clients for load testing:**
```bash
cd docker
docker-compose up --build --scale c2_client=10
```

**Interact with the server CLI:**
The server terminal is interactive. Type commands directly:
```
C2> list
C2> db events 20
C2> bash <client_id> whoami
```

**Stop all services:**
```bash
cd docker
docker-compose down
```

**Clean up (remove volumes):**
```bash
cd docker
docker-compose down -v
```

### Option 2: Local Development (Python)

For development and testing without Docker:

**Install Dependencies:**
```bash
pip3 install -r requirements.txt
```

**Start Database:**
```bash
cd docker
docker-compose up postgres -d
```

**Terminal 1 - Start the Server:**
```bash
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

**Terminal 2 - Start a Client:**
```bash
python3 client/c2_client.py
```

You should see:
```
Connected to C2 Server. Client ID: abc-123-def-456...
```

**Stop database:**
```bash
cd docker
docker-compose down
```

### Testing the System

Whether using Docker or local Python:

1. **List clients**: Type `list` in server CLI
2. **Test echo**: `echo <client_id> Hello World`
3. **Test bash**: `bash <client_id> ls -la`
4. **Query database**: `db events 10`
5. **Test kill**: `kill <client_id>`
6. **Exit**: `exit`

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

**Query database events:**
```
C2> db events [limit]
```
Example:
```
C2> db events 20
```

**Query database commands:**
```
C2> db commands [limit]
```

**Query database results:**
```
C2> db results [limit]
```

**Show help:**
```
C2> help
```

**Exit server:**
```
C2> exit
```

### Querying the Database (Step 3)

**Option 1: Query from Server CLI (Recommended)**

The server CLI provides built-in commands to query the database:

```
C2> db events 10
```
Shows recent events including:
- Client connections/disconnections
- Heartbeats from clients (logged every 30 seconds)

```
C2> db commands 10
```
Shows recently sent commands with type and command text.

```
C2> db results 10
```
Shows command execution results with success status.

**Option 2: Direct Database Access**

**Connect to database:**
```bash
docker exec -it c2_postgres psql -U c2admin -d c2_logs
```

**View logged events:**
```sql
SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;
```

**View sent commands:**
```sql
SELECT * FROM commands ORDER BY timestamp DESC LIMIT 10;
```

**View command results:**
```sql
SELECT * FROM results ORDER BY timestamp DESC LIMIT 10;
```

**Join commands with their results:**
```sql
SELECT c.timestamp, c.client_id, c.command, r.success, r.result
FROM commands c
LEFT JOIN results r ON c.command_id = r.command_id
ORDER BY c.timestamp DESC;
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
│   ├── protocol.py       # Message framing & encryption
│   ├── db_logger.py      # Database logging
│   └── init_db.sql       # Database schema
├── client/
│   ├── __init__.py
│   ├── c2_client.py      # Demo client/agent
│   └── command_executor.py  # Command execution logic
├── docker/
│   ├── Dockerfile.postgres  # PostgreSQL container
│   ├── Dockerfile.server    # C2 server container
│   ├── Dockerfile.client    # C2 client container
│   ├── docker-compose.yml   # Complete infrastructure
│   └── .dockerignore        # Docker build exclusions
├── tests/
│   ├── test_protocol.py     # Protocol tests
│   ├── test_encryption.py   # Encryption tests
│   ├── test_cd_command.py   # CD command tests
│   └── test_integration.py  # Integration tests
├── config.py             # Centralized configuration
├── requirements.txt      # Python dependencies
├── load_test.py          # Automated load testing script
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

### ✅ Step 3 - Microservice Architecture (COMPLETED)
- [x] PostgreSQL database setup with Docker Compose
- [x] Log all events to database (client connect/disconnect, heartbeats)
- [x] Store commands and results in database
- [x] Database logger with connection pooling
- [x] CLI commands for querying database (db events/commands/results)
- [x] Database logging tests passing (1/1)

### ✅ Step 4 - Advanced Functionality (COMPLETED)
- [x] Bash command execution (implemented)
- [x] Async command queue (implemented)
- [x] Heartbeat mechanism (implemented)
- [x] Async server (non-blocking)
- [x] Load tested with many clients (385 connections/sec, handles 100+ concurrent clients)

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

## Load Testing

The project includes an automated load testing script to measure server performance:

**Run load test:**
```bash
python3 load_test.py --clients 50 --commands 10 --duration 10
```

**Parameters:**
- `--host`: Server host (default: 127.0.0.1)
- `--port`: Server port (default: 8888)
- `--clients`: Number of concurrent clients (default: 10)
- `--commands`: Commands per client for throughput test (default: 10)
- `--duration`: Sustained load test duration in seconds (default: 10)

**Test Results (Example):**
```
Test 1: Connection Load
  - Connected 20/20 clients
  - Rate: 385.4 connections/sec

Test 2: Command Throughput
  - Executed commands across all clients
  - Measured response times and success rates

Test 3: Sustained Load
  - Continuous command execution for specified duration
  - Average rate and failure rate tracked
```

**Scaling with Docker:**
```bash
cd docker
docker compose up --build --scale c2_client=100
```

The server has been tested with 100+ concurrent clients successfully.

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