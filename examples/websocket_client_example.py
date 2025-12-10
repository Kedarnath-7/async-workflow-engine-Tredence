"""
WebSocket Client Example - Stream workflow execution logs in real-time.

This demonstrates how to connect to the workflow engine's WebSocket endpoint
to receive live execution updates.

Usage:
    python websocket_client_example.py <run_id>
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime


async def stream_workflow_logs(run_id: str, base_url: str = "localhost:8000"):
    """
    Connect to workflow WebSocket and stream logs in real-time.
    
    Args:
        run_id: The workflow run ID to monitor
        base_url: WebSocket server address (default: localhost:8000)
    """
    uri = f"ws://{base_url}/graph/ws/run/{run_id}"
    
    print(f"Connecting to workflow: {run_id}")
    print(f"WebSocket URI: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[INFO] Connected successfully. Streaming logs...")
            
            # Send ping to keep connection alive
            async def send_ping():
                while True:
                    await asyncio.sleep(30)
                    try:
                        await websocket.send("ping")
                    except:
                        break
            
            # Start ping task
            ping_task = asyncio.create_task(send_ping())
            
            try:
                # Receive and display messages
                async for message in websocket:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "log":
                        # Execution step log
                        node_id = data.get("node_id", "unknown")
                        log_data = data.get("data", {})
                        duration = log_data.get("duration_ms", 0)
                        
                        print(f"[LOG] Node: {node_id:<15} Duration: {duration:.2f}ms")
                        
                    elif message_type == "status":
                        # Status update
                        status = data.get("status", "unknown")
                        msg = data.get("message", "")
                        
                        print(f"[STATUS] {status.upper()}: {msg}")
                        
                        # Exit on completion or failure
                        if status in ["completed", "failed"]:
                            print("[INFO] Disconnecting...")
                            break
                    
                    else:
                        print(f"[WARN] Unknown message type: {message_type}")
            
            finally:
                ping_task.cancel()
                
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code == 1008:
            print(f"[ERROR] Run ID '{run_id}' not found.")
        else:
            print(f"[ERROR] Connection error: {e}")
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to {base_url}. Ensure server is running.")
    except KeyboardInterrupt:
        print("\n[INFO] Disconnected by user.")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python websocket_client_example.py <run_id> [server_url]")
        print("\nExample:")
        print("  python websocket_client_example.py abc123-def456-789")
        print("  python websocket_client_example.py abc123 localhost:8000")
        sys.exit(1)
    
    run_id = sys.argv[1]
    server_url = sys.argv[2] if len(sys.argv) > 2 else "localhost:8000"
    
    await stream_workflow_logs(run_id, server_url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
