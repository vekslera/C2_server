-- Database schema for C2 Server logging
-- Citation: PostgreSQL documentation for table creation
-- https://www.postgresql.org/docs/current/sql-createtable.html

-- Events table: logs client connections, disconnections, and other events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(50) NOT NULL,
    client_id VARCHAR(100),
    details TEXT
);

-- Commands table: logs all commands sent to clients
CREATE TABLE IF NOT EXISTS commands (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    client_id VARCHAR(100) NOT NULL,
    command_id VARCHAR(100) NOT NULL,
    command_type VARCHAR(50) NOT NULL,
    command TEXT NOT NULL
);

-- Results table: logs command execution results
CREATE TABLE IF NOT EXISTS results (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    client_id VARCHAR(100) NOT NULL,
    command_id VARCHAR(100) NOT NULL,
    result TEXT,
    success BOOLEAN DEFAULT true
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_events_client_id ON events(client_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_commands_client_id ON commands(client_id);
CREATE INDEX IF NOT EXISTS idx_commands_command_id ON commands(command_id);
CREATE INDEX IF NOT EXISTS idx_results_command_id ON results(command_id);
