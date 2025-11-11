#!/usr/bin/env python3
"""
TRACKING SERVER - Centralized Coordinator
Manages authentication, peer registration, and channel metadata
"""

import json
import socket
import time
from datetime import datetime
from daemon.weaprous import WeApRous

# Configuration
TRACKER_PORT = 8000

# Global data structures
users = {"admin": "password", "user1": "pass1", "user2": "pass2"}
active_peers = {}  # {peer_id: {"ip": ip, "port": port, "username": username, "last_seen": timestamp}}
channels = {}      # {channel_name: {"members": [peer_addresses], "created": timestamp}}
sessions = {}      # {username: {"logged_in": True, "timestamp": timestamp}}

# Initialize tracker app
tracker_app = WeApRous()

def json_response(data):
    """Convert dictionary to JSON string for response"""
    return json.dumps(data, indent=2)


@tracker_app.route('/login_app', methods=['POST'])
def login(headers, body):
    """
    POST /login
    Authenticate user credentials and create session
    
    Request body: {"username": "admin", "password": "password"}
    Response: {"status": "success/error", "message": "...", "username": "..."}
    """
    try:
        # Parse JSON body
        data = json.loads(body) if body else {}
        username = data.get('username', '')
        password = data.get('password', '')
        
        print("[Tracker] Login attempt: username={}".format(username))
        
        # Validate credentials
        if username in users and users[username] == password:
            # Create session
            sessions[username] = {
                "logged_in": True,
                "timestamp": datetime.now().isoformat()
            }
            
            response = {
                "status": "success",
                "message": "Login successful",
                "username": username,
                "timestamp": datetime.now().isoformat()
            }
            print("[Tracker] Login successful for user: {}".format(username))
        else:
            response = {
                "status": "error",
                "message": "Invalid username or password"
            }
            print("[Tracker] Login failed for user: {}".format(username))
        
        return json_response(response)
    
    except Exception as e:
        print("[Tracker] Login error: {}".format(e))
        return json_response({
            "status": "error",
            "message": "Server error: {}".format(str(e))
        })


@tracker_app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    POST /submit-info
    Register or update peer's IP, port, and username
    
    Request body: {"username": "admin", "ip": "127.0.0.1", "port": 7000}
    Response: {"status": "success/error", "peer_address": "127.0.0.1:7000"}
    """
    try:
        data = json.loads(body) if body else {}
        username = data.get('username', '')
        peer_ip = data.get('ip', '')
        peer_port = data.get('port', 0)
        
        print("[Tracker] Submit-info: username={}, ip={}, port={}".format(
            username, peer_ip, peer_port))
        
        # Validate input
        if not username or not peer_ip or not peer_port:
            return json_response({
                "status": "error",
                "message": "Missing required fields: username, ip, port"
            })
        
        # Check if user is logged in
        if username not in sessions or not sessions[username].get("logged_in"):
            return json_response({
                "status": "error",
                "message": "User not logged in. Please login first."
            })
        
        # Create peer address
        peer_address = "{}:{}".format(peer_ip, peer_port)
        
        # Register or update peer
        active_peers[peer_address] = {
            "username": username,
            "ip": peer_ip,
            "port": peer_port,
            "peer_address": peer_address,
            "last_seen": time.time(),
            "timestamp": datetime.now().isoformat()
        }
        
        response = {
            "status": "success",
            "message": "Peer registered successfully",
            "peer_address": peer_address,
            "username": username
        }
        
        print("[Tracker] Peer registered: {} at {}".format(username, peer_address))
        return json_response(response)
    
    except Exception as e:
        print("[Tracker] Submit-info error: {}".format(e))
        return json_response({
            "status": "error",
            "message": "Registration failed: {}".format(str(e))
        })


@tracker_app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """
    GET /get-list
    Return list of all active peers and available channels
    
    Response: {
        "status": "success",
        "peers": [...],
        "channels": {...}
    }
    """
    try:
        print("[Tracker] Get-list request")
        
        # Clean up stale peers (inactive for more than 50 minutes)
        current_time = time.time()
        stale_peers = []
        for peer_addr, peer_info in active_peers.items():
            if current_time - peer_info.get("last_seen", 0) > 3000:
                stale_peers.append(peer_addr)
        
        for peer_addr in stale_peers:
            del active_peers[peer_addr]
            print("[Tracker] Removed stale peer: {}".format(peer_addr))
        
        # Prepare peer list
        peers_list = []
        for peer_addr, peer_info in active_peers.items():
            peers_list.append({
                "peer_address": peer_addr,
                "username": peer_info.get("username"),
                "ip": peer_info.get("ip"),
                "port": peer_info.get("port")
            })
        
        response = {
            "status": "success",
            "peers": peers_list,
            "channels": channels,
            "peer_count": len(peers_list),
            "channel_count": len(channels),
            "timestamp": datetime.now().isoformat()
        }
        
        print("[Tracker] Returning {} peers and {} channels".format(
            len(peers_list), len(channels)))
        
        return json_response(response)
    
    except Exception as e:
        print("[Tracker] Get-list error: {}".format(e))
        return json_response({
            "status": "error",
            "message": "Failed to retrieve list: {}".format(str(e))
        })

@tracker_app.route('/add-list', methods=['POST'])
def add_list(headers, body):
    """
    POST /add-list
    Create a new channel or add a peer to an existing channel
    
    Request body: {
        "username": "admin",
        "channel": "general",
        "peer_address": "127.0.0.1:7000"
    }
    Response: {
        "status": "success",
        "channel": "general",
        "members": [...]
    }
    """
    try:
        data = json.loads(body) if body else {}
        username = data.get('username', '')
        channel_name = data.get('channel', '')
        peer_address = data.get('peer_address', '')
        
        print("[Tracker] Add-list: username={}, channel={}, peer={}".format(
            username, channel_name, peer_address))
        
        # Validate input
        if not username or not channel_name or not peer_address:
            return json_response({
                "status": "error",
                "message": "Missing required fields: username, channel, peer_address"
            })
        
        # Check if user is logged in
        if username not in sessions or not sessions[username].get("logged_in"):
            return json_response({
                "status": "error",
                "message": "User not logged in"
            })
        
        # Check if peer is registered
        if peer_address not in active_peers:
            return json_response({
                "status": "error",
                "message": "Peer not registered. Call /submit-info first."
            })
        
        # Create channel if doesn't exist
        if channel_name not in channels:
            channels[channel_name] = {
                "members": [],
                "created": datetime.now().isoformat()
            }
            print("[Tracker] Created new channel: {}".format(channel_name))
        
        # Add peer to channel if not already a member
        if peer_address not in channels[channel_name]["members"]:
            channels[channel_name]["members"].append(peer_address)
            message = "Joined channel successfully"
        else:
            message = "Already a member of this channel"
        
        response = {
            "status": "success",
            "message": message,
            "channel": channel_name,
            "members": channels[channel_name]["members"],
            "member_count": len(channels[channel_name]["members"])
        }
        
        print("[Tracker] {} added to channel {}. Total members: {}".format(
            peer_address, channel_name, len(channels[channel_name]["members"])))
        
        return json_response(response)
    
    except Exception as e:
        print("[Tracker] Add-list error: {}".format(e))
        return json_response({
            "status": "error",
            "message": "Failed to join channel: {}".format(str(e))
        })


@tracker_app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    """
    POST /connect-peer
    Return connection details (IP and port) of a requested peer
    
    Request body: {"peer_address": "127.0.0.1:7001"}
    Response: {
        "status": "success",
        "peer": {"ip": "127.0.0.1", "port": 7001, "username": "user1"}
    }
    """
    try:
        data = json.loads(body) if body else {}
        peer_address = data.get('peer_address', '')
        
        print("[Tracker] Connect-peer request for: {}".format(peer_address))
        
        if not peer_address:
            return json_response({
                "status": "error",
                "message": "Missing peer_address"
            })
        
        # Find peer
        if peer_address in active_peers:
            peer_info = active_peers[peer_address]
            response = {
                "status": "success",
                "peer": {
                    "peer_address": peer_address,
                    "username": peer_info.get("username"),
                    "ip": peer_info.get("ip"),
                    "port": peer_info.get("port")
                }
            }
            print("[Tracker] Found peer: {}".format(peer_address))
        else:
            response = {
                "status": "error",
                "message": "Peer not found: {}".format(peer_address)
            }
            print("[Tracker] Peer not found: {}".format(peer_address))
        
        return json_response(response)
    
    except Exception as e:
        print("[Tracker] Connect-peer error: {}".format(e))
        return json_response({
            "status": "error",
            "message": "Failed to connect: {}".format(str(e))
        })


def main_tracker():
    """Start the tracking server"""
    print("=" * 70)
    print("TRACKING SERVER - Centralized Coordinator")
    print("=" * 70)
    print("Port: {}".format(TRACKER_PORT))
    print()
    print("Available APIs:")
    print("  POST /login          - Authenticate user")
    print("  POST /submit-info    - Register peer")
    print("  GET  /get-list       - Get peers and channels")
    print("  POST /add-list       - Join/create channel")
    print("  POST /connect-peer   - Get peer connection info")
    print("=" * 70)
    print()
    
    tracker_app.prepare_address("127.0.0.1", TRACKER_PORT)
    tracker_app.run()


# =============================================================================
# PEER NODE - Decentralized Chat Participant
# =============================================================================

def create_peer_app(peer_config):
    """
    Create a peer application that acts as both client and server
    
    peer_config = {
        "username": "admin",
        "ip": "127.0.0.1",
        "port": 7000,
        "tracker_url": "127.0.0.1:8000"
    }
    """
    
    # Peer's local storage
    peer_data = {
        "username": peer_config["username"],
        "ip": peer_config["ip"],
        "port": peer_config["port"],
        "peer_address": "{}:{}".format(peer_config["ip"], peer_config["port"]),
        "channels": {},  # {channel_name: {"messages": [], "members": []}}
        "direct_messages": {}  # {peer_address: [messages]}
    }
    
    peer_app = WeApRous()
    
    @peer_app.route('/send-peer', methods=['POST'])
    def send_peer(headers, body):
        """
        POST /send-peer
        Receive a direct message from another peer
        
        Request body: {
            "from": "127.0.0.1:7000",
            "username": "admin",
            "message": "Hello!"
        }
        """
        try:
            data = json.loads(body) if body else {}
            from_address = data.get('from', '')
            to_address = data.get('to','')
            from_username = data.get('username', '')
            message_text = data.get('message', '')
            
            print("[Peer {}] Received direct message from {}: {}".format(
                peer_config["port"], from_username, message_text))
            
            if not from_address or not message_text:
                return json_response({
                    "status": "error",
                    "message": "Missing from or message field"
                })
            
            # Determine where to store the message
            store_key = to_address if to_address else from_address
            # Store direct message
            if store_key not in peer_data["direct_messages"]:
                peer_data["direct_messages"][store_key] = []
            
            message_entry = {
                "from": from_address,
                "username": from_username,
                "message": message_text,
                "timestamp": datetime.now().isoformat(),
                "type": "direct"
            }
            
            peer_data["direct_messages"][store_key].append(message_entry)
            
            response = {
                "status": "success",
                "message": "Direct message received and stored"
            }
            
            return json_response(response)
        
        except Exception as e:
            print("[Peer {}] Send-peer error: {}".format(peer_config["port"], e))
            return json_response({
                "status": "error",
                "message": "Failed to receive message: {}".format(str(e))
            })
    
    @peer_app.route('/broadcast-peer', methods=['POST'])
    def broadcast_peer(headers, body):
        """
        POST /broadcast-peer
        Receive a broadcast message for a channel
        
        Request body: {
            "channel": "general",
            "from": "127.0.0.1:7000",
            "username": "admin",
            "message": "Hello everyone!"
        }
        """
        try:
            data = json.loads(body) if body else {}
            channel_name = data.get('channel', '')
            from_address = data.get('from', '')
            from_username = data.get('username', '')
            message_text = data.get('message', '')
            sync_mode = data.get('sync', False)
            messages = data.get('messages')  # could be an array when sync=True
            
            print("[Peer {}] Received broadcast in '{}' from {}: {}".format(
                peer_config["port"], channel_name, from_username, message_text))
            
            if sync_mode and isinstance(messages, list):
                # Import multiple historical messages
                if channel_name not in peer_data["channels"]:
                    peer_data["channels"][channel_name] = {"messages": []}
                peer_data["channels"][channel_name]["messages"].extend(messages)
                print(f"[Peer {peer_config['port']}] Synced {len(messages)} old messages to {channel_name}")
                return json_response({"status": "success", "message": "History imported"})
            
            if not channel_name or not message_text:
                return json_response({
                    "status": "error",
                    "message": "Missing channel or message field"
                })
            
            # Create channel if doesn't exist
            if channel_name not in peer_data["channels"]:
                peer_data["channels"][channel_name] = {
                    "messages": [],
                    "members": []
                }
            
            # Store message
            message_entry = {
                "from": from_address,
                "username": from_username,
                "message": message_text,
                "timestamp": datetime.now().isoformat(),
                "type": "broadcast",
                "channel": channel_name
            }
            
            peer_data["channels"][channel_name]["messages"].append(message_entry)
            
            response = {
                "status": "success",
                "message": "Broadcast message received and stored",
                "channel": channel_name
            }
            
            return json_response(response)
        
        except Exception as e:
            print("[Peer {}] Broadcast-peer error: {}".format(peer_config["port"], e))
            return json_response({
                "status": "error",
                "message": "Failed to receive broadcast: {}".format(str(e))
            })
    
    @peer_app.route('/get-messages', methods=['POST'])
    def get_messages(headers, body):
        """
        GET /get-messages?channel=general
        Retrieve locally stored messages of a channel
        
        Response: {
            "status": "success",
            "channel": "general",
            "messages": [...]
        }
        """
        try:
            # Simple query parameter parsing (channel name assumed in body or default)
            channel_name = "general"  # Default channel
            
            if body:
                try:
                    data = json.loads(body)
                    channel_name = data.get('channel', 'general')
                except:
                    pass
            
            print("[Peer {}] Get-messages request for channel: {}".format(
                peer_config["port"], channel_name))
            
            if channel_name in peer_data["channels"]:
                messages = peer_data["channels"][channel_name]["messages"]
            else:
                messages = []
            
            response = {
                "status": "success",
                "channel": channel_name,
                "messages": messages,
                "message_count": len(messages)
            }
            
            return json_response(response)
        
        except Exception as e:
            print("[Peer {}] Get-messages error: {}".format(peer_config["port"], e))
            return json_response({
                "status": "error",
                "message": "Failed to retrieve messages: {}".format(str(e))
            })
    
    @peer_app.route('/get-peer-messages', methods=['POST'])
    def get_peer_messages(headers, body):
        """
        POST /get-peer-messages
        Retrieve direct messages with a specific peer
        
        Request body: {
            "peer_address": "127.0.0.1:7001"  // The peer you want to see messages from
        }
        
        Response: {
            "status": "success",
            "peer_address": "127.0.0.1:7001",
            "messages": [
                {
                    "from": "127.0.0.1:7001",
                    "username": "user1",
                    "message": "Hello!",
                    "timestamp": "2025-11-05T10:30:00",
                    "type": "direct"
                },
                ...
            ],
            "message_count": 5
        }
        """
        try:
            if not body:
                return json_response({
                    "status": "error",
                    "message": "Missing body"
                })
            
            data = json.loads(body)
            peer_address = data.get('peer_address', '')
            
            if not peer_address:
                return json_response({
                    "status": "error",
                    "message": "Missing peer address"
                })
            
            print("[Peer {}] Get-peer-messages request for peer: {}".format(
                peer_config["port"], peer_address))
            
            # Get messages from this specific peer
            messages = []
            if peer_address in peer_data["direct_messages"]:
                messages = peer_data["direct_messages"][peer_address]
            
            result = {
                "status": "success",
                "peer_address": peer_address,
                "messages": messages,
                "message_count": len(messages),
                "current_peer": peer_data["peer_address"]
            }
            
            print("[Peer {}] Found {} messages from {}".format(
                peer_config["port"], len(messages), peer_address))
            
            return json_response(result)

        except Exception as e:
            print("[Peer {}] Get-messages error: {}".format(peer_config["port"], e))
            return json_response({
                "status": "error",
                "message": "Failed to retrieve messages: {}".format(str(e))
            })
    return peer_app, peer_data

def main_peer():
    """Start a peer node"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Peer Node')
    parser.add_argument('--username', default='admin', help='Username')
    parser.add_argument('--ip', default='127.0.0.1', help='IP address')
    parser.add_argument('--port', type=int, required=True, help='Port number')
    parser.add_argument('--tracker', default='127.0.0.1:8000', help='Tracker address')
    
    args = parser.parse_args()
    
    peer_config = {
        "username": args.username,
        "ip": args.ip,
        "port": args.port,
        "tracker_url": args.tracker
    }
    
    print("=" * 70)
    print("PEER NODE - {}".format(peer_config["username"]))
    print("=" * 70)
    print("Peer Address: {}:{}".format(peer_config["ip"], peer_config["port"]))
    print("Tracker: {}".format(peer_config["tracker_url"]))
    print()
    print("Available APIs:")
    print("  POST /send-peer       - Receive direct message")
    print("  POST /broadcast-peer  - Receive broadcast message")
    print("  GET  /get-messages    - Get channel messages")
    print("  GET  /channels        - Get joined channels")
    print("=" * 70)
    print()
    
    peer_app, peer_data = create_peer_app(peer_config)
    peer_app.prepare_address(peer_config["ip"], peer_config["port"])
    peer_app.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "tracker":
        main_tracker()
    elif len(sys.argv) > 1 and sys.argv[1] == "peer":
        # Remove 'peer' argument and pass rest to peer
        sys.argv.pop(1)
        main_peer()
    else:
        print("Usage:")
        print("  python chat_app.py tracker")
        print("  python chat_app.py peer --port 7000 --username admin")