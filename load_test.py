"""
Load Testing Script for C2 Server
Connects multiple clients, sends commands, and measures performance
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import sys
sys.path.insert(0, '.')

from server.protocol import ProtocolHandler
import config


class LoadTestClient:
    """Simplified client for load testing"""

    def __init__(self, client_id: int, use_ecdh: bool = True):
        self.client_id = client_id
        self.use_ecdh = use_ecdh
        self.protocol = None
        self.reader = None
        self.writer = None
        self.connected = False
        self.response_times: List[float] = []
        self.errors = 0

    async def connect(self, host: str, port: int) -> bool:
        """Connect to the C2 server"""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=10.0
            )

            # Initialize protocol handler
            if self.use_ecdh:
                self.protocol = ProtocolHandler(use_ecdh=True)
            else:
                encryption_key = config.ENCRYPTION_PSK if hasattr(config, 'ENCRYPTION_PSK') else None
                self.protocol = ProtocolHandler(encryption_key)

            # Perform ECDH key exchange if enabled
            if self.use_ecdh:
                # Receive server's public key (32 bytes)
                server_pubkey = await asyncio.wait_for(
                    self.reader.read(32),
                    timeout=5.0
                )
                if len(server_pubkey) != 32:
                    self.errors += 1
                    return False

                # Send client's public key
                client_pubkey = self.protocol.get_public_key_bytes()
                self.writer.write(client_pubkey)
                await self.writer.drain()

                # Derive shared encryption key
                self.protocol.derive_shared_key(server_pubkey)

            # Read welcome message
            welcome = await asyncio.wait_for(
                self.protocol.read_message(self.reader),
                timeout=5.0
            )

            if welcome and welcome.get("type") == "welcome":
                self.connected = True
                return True
            return False
        except Exception as e:
            self.errors += 1
            return False

    async def send_command(self, command_type: str, data: str) -> float:
        """Send a command and measure response time"""
        if not self.connected:
            return -1.0

        try:
            start_time = time.time()

            # Send heartbeat command
            from datetime import datetime
            await self.protocol.write_message(self.writer, {
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            })

            # Wait for response
            response = await asyncio.wait_for(
                self.protocol.read_message(self.reader),
                timeout=5.0
            )

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            if response and response.get("type") == "heartbeat_ack":
                self.response_times.append(response_time)
                return response_time
            else:
                self.errors += 1
                return -1.0

        except Exception as e:
            self.errors += 1
            return -1.0

    async def disconnect(self):
        """Close connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False


class LoadTester:
    """Main load testing orchestrator"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8888, use_ecdh: bool = True):
        self.host = host
        self.port = port
        self.use_ecdh = use_ecdh
        self.clients: List[LoadTestClient] = []

    async def test_connection_load(self, num_clients: int) -> Dict[str, Any]:
        """Test server's ability to handle multiple simultaneous connections"""
        print(f"\n{'='*60}")
        print(f"TEST 1: Connection Load Test - {num_clients} clients")
        print(f"{'='*60}")

        start_time = time.time()

        # Create clients
        self.clients = [LoadTestClient(i, self.use_ecdh) for i in range(num_clients)]

        # Connect all clients in parallel
        print(f"Connecting {num_clients} clients...")
        connect_tasks = [client.connect(self.host, self.port) for client in self.clients]
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        end_time = time.time()

        # Calculate statistics
        successful = sum(1 for r in results if r is True)
        failed = num_clients - successful
        total_time = end_time - start_time

        print(f"\nResults:")
        print(f"  ✓ Connected:     {successful}/{num_clients}")
        print(f"  ✗ Failed:        {failed}/{num_clients}")
        print(f"  ⏱ Total Time:    {total_time:.2f}s")
        print(f"  ⚡ Rate:          {successful/total_time:.1f} connections/sec")

        return {
            "test": "connection_load",
            "num_clients": num_clients,
            "successful": successful,
            "failed": failed,
            "total_time": total_time,
            "rate": successful/total_time if total_time > 0 else 0
        }

    async def test_command_throughput(self, num_commands: int) -> Dict[str, Any]:
        """Test command execution throughput"""
        print(f"\n{'='*60}")
        print(f"TEST 2: Command Throughput - {num_commands} commands/client")
        print(f"{'='*60}")

        connected_clients = [c for c in self.clients if c.connected]
        if not connected_clients:
            print("ERROR: No connected clients!")
            return {}

        print(f"Sending {num_commands} commands to each of {len(connected_clients)} clients...")

        start_time = time.time()

        # Send commands from all clients in parallel
        tasks = []
        for client in connected_clients:
            for i in range(num_commands):
                tasks.append(client.send_command("echo", f"Test message {i}"))

        response_times = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()

        # Filter out errors and calculate statistics
        valid_times = [t for t in response_times if isinstance(t, float) and t > 0]
        total_commands = len(tasks)
        successful = len(valid_times)
        failed = total_commands - successful
        total_time = end_time - start_time

        print(f"\nResults:")
        print(f"  ✓ Successful:    {successful}/{total_commands}")
        print(f"  ✗ Failed:        {failed}/{total_commands}")
        print(f"  ⏱ Total Time:    {total_time:.2f}s")
        print(f"  ⚡ Throughput:    {successful/total_time:.1f} commands/sec")

        if valid_times:
            print(f"\nResponse Times:")
            print(f"  Min:             {min(valid_times):.2f}ms")
            print(f"  Max:             {max(valid_times):.2f}ms")
            print(f"  Avg:             {statistics.mean(valid_times):.2f}ms")
            print(f"  Median:          {statistics.median(valid_times):.2f}ms")
            if len(valid_times) > 1:
                print(f"  StdDev:          {statistics.stdev(valid_times):.2f}ms")

        return {
            "test": "command_throughput",
            "total_commands": total_commands,
            "successful": successful,
            "failed": failed,
            "total_time": total_time,
            "throughput": successful/total_time if total_time > 0 else 0,
            "response_times": {
                "min": min(valid_times) if valid_times else 0,
                "max": max(valid_times) if valid_times else 0,
                "avg": statistics.mean(valid_times) if valid_times else 0,
                "median": statistics.median(valid_times) if valid_times else 0,
                "stdev": statistics.stdev(valid_times) if len(valid_times) > 1 else 0
            }
        }

    async def test_sustained_load(self, duration_seconds: int) -> Dict[str, Any]:
        """Test server under sustained load"""
        print(f"\n{'='*60}")
        print(f"TEST 3: Sustained Load - {duration_seconds}s duration")
        print(f"{'='*60}")

        connected_clients = [c for c in self.clients if c.connected]
        if not connected_clients:
            print("ERROR: No connected clients!")
            return {}

        print(f"Running sustained load test with {len(connected_clients)} clients...")
        print("Each client sends commands continuously")

        total_commands = 0
        successful = 0
        start_time = time.time()
        end_time = start_time + duration_seconds

        async def send_continuous_commands(client: LoadTestClient):
            nonlocal total_commands, successful
            while time.time() < end_time:
                total_commands += 1
                result = await client.send_command("echo", "Sustained test")
                if result > 0:
                    successful += 1
                await asyncio.sleep(0.1)  # Small delay between commands

        # Run all clients in parallel
        await asyncio.gather(*[send_continuous_commands(c) for c in connected_clients])

        actual_duration = time.time() - start_time
        failed = total_commands - successful

        print(f"\nResults:")
        print(f"  ⏱ Duration:      {actual_duration:.2f}s")
        print(f"  ✓ Successful:    {successful}/{total_commands}")
        print(f"  ✗ Failed:        {failed}/{total_commands}")
        print(f"  ⚡ Avg Rate:      {successful/actual_duration:.1f} commands/sec")

        return {
            "test": "sustained_load",
            "duration": actual_duration,
            "total_commands": total_commands,
            "successful": successful,
            "failed": failed,
            "rate": successful/actual_duration if actual_duration > 0 else 0
        }

    async def cleanup(self):
        """Disconnect all clients"""
        print(f"\nCleaning up...")
        await asyncio.gather(*[client.disconnect() for client in self.clients])
        print(f"All clients disconnected.")

    async def run_full_test(self, num_clients: int = 10, commands_per_client: int = 10, sustained_duration: int = 10):
        """Run complete load test suite"""
        print(f"\n{'#'*60}")
        print(f"# C2 Server Load Test Suite")
        print(f"# Target: {self.host}:{self.port}")
        print(f"{'#'*60}")

        results = []

        try:
            # Test 1: Connection load
            result1 = await self.test_connection_load(num_clients)
            results.append(result1)

            await asyncio.sleep(2)  # Wait for stabilization

            # Test 2: Command throughput
            result2 = await self.test_command_throughput(commands_per_client)
            results.append(result2)

            await asyncio.sleep(2)  # Wait for stabilization

            # Test 3: Sustained load
            result3 = await self.test_sustained_load(sustained_duration)
            results.append(result3)

        finally:
            await self.cleanup()

        # Print summary
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Test 1: Connection Load")
        print(f"  - Connected {result1.get('successful', 0)}/{result1.get('num_clients', 0)} clients")
        print(f"  - Rate: {result1.get('rate', 0):.1f} connections/sec")

        if result2:
            print(f"\nTest 2: Command Throughput")
            print(f"  - Executed {result2.get('successful', 0)}/{result2.get('total_commands', 0)} commands")
            print(f"  - Throughput: {result2.get('throughput', 0):.1f} commands/sec")
            print(f"  - Avg Response: {result2.get('response_times', {}).get('avg', 0):.2f}ms")

        if result3:
            print(f"\nTest 3: Sustained Load")
            print(f"  - Executed {result3.get('successful', 0)}/{result3.get('total_commands', 0)} commands")
            print(f"  - Rate: {result3.get('rate', 0):.1f} commands/sec")

        print(f"\n{'='*60}")
        print(f"Load test completed!")
        print(f"{'='*60}\n")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="C2 Server Load Testing Tool")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8888, help="Server port (default: 8888)")
    parser.add_argument("--clients", type=int, default=10, help="Number of clients (default: 10)")
    parser.add_argument("--commands", type=int, default=10, help="Commands per client (default: 10)")
    parser.add_argument("--duration", type=int, default=10, help="Sustained load duration in seconds (default: 10)")
    parser.add_argument("--use-ecdh", action="store_true", default=True, help="Use ECDH encryption (default: True)")
    parser.add_argument("--use-psk", action="store_true", help="Use PSK encryption instead of ECDH")

    args = parser.parse_args()

    # Use PSK if explicitly requested, otherwise use ECDH
    use_ecdh = not args.use_psk

    tester = LoadTester(host=args.host, port=args.port, use_ecdh=use_ecdh)
    await tester.run_full_test(
        num_clients=args.clients,
        commands_per_client=args.commands,
        sustained_duration=args.duration
    )


if __name__ == "__main__":
    asyncio.run(main())
