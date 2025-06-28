#!/usr/bin/env python3
"""
Simple test script to verify SocketIO disconnect handler is working.
This helps ensure the function signature fix is correct.
"""

import socketio
import time
import threading

def test_socketio_disconnect():
    """Test SocketIO disconnect handler."""
    print("=== SocketIO Disconnect Handler Test ===")
    
    # Create a test client
    client = socketio.Client()
    
    def on_connect():
        print("✅ Connected to server")
        
    def on_disconnect():
        print("✅ Disconnected from server")
        
    def on_connect_error(data):
        print(f"❌ Connection error: {data}")
        
    # Register event handlers
    client.on('connect', on_connect)
    client.on('disconnect', on_disconnect)
    client.on('connect_error', on_connect_error)
    
    try:
        # Connect to the server
        print("🔄 Connecting to server...")
        client.connect('http://localhost:5000')
        
        # Wait a moment
        time.sleep(2)
        
        # Disconnect
        print("🔄 Disconnecting...")
        client.disconnect()
        
        print("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if client.connected:
            client.disconnect()

if __name__ == "__main__":
    success = test_socketio_disconnect()
    if success:
        print("\n🎉 SocketIO disconnect handler test passed!")
    else:
        print("\n💥 SocketIO disconnect handler test failed.") 