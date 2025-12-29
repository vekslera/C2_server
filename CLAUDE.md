# C2_server Project

## Overview
A C2 (Command & Control) server and demo client for a cyber security coding exercise.
4-hour time limit. Prioritize Steps 1-3, partial Step 4.

## Architecture Decisions
- Python 3.10 with asyncio throughout
- Raw TCP with length-prefixed framing (4-byte header)
- AES-256-GCM encryption (PSK initially, upgrade to ECDH if time permits)
- PostgreSQL via Docker for logging (Step 3)
- Message format: JSON payloads

## Project Structure
- server/ — C2 server + CLI
- client/ — Demo agent
- docker-compose.yml — Postgres + server

## Step Priority
1. Basic connectivity, CLI, echo/kill commands
2. Encryption (PSK + AES-GCM)
3. Microservice (Postgres logging)
4. Advanced (heartbeat, async queue) — partial OK
5. Testing — minimal but cover the main functionality.

## Code Style
- Type hints on all functions
- Async functions prefixed with clear names
- Comments explaining protocol choices (for interview discussion)

## Citation Requirement
Assignment requires citing external code snippets. Add source comments.

## Coding Style
Absolutely no hardcoded values (use config.py when necessary)!
SOLID principles, especially concern separation (Single Responsibility), and abstraction (Dependency Inversion) principles.
Keep README.md concise and well-updated at each step.
Commit changes after each coding step.