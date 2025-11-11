#!/usr/bin/env python3
"""
Chat Client Utility - For interacting with tracker and peers
Demonstrates complete workflow: login → register → join channel → send messages
"""

import socket
import json
import time


def send_json_request(method, ip, port, path, data=None):
    """
    Send HTTP request with JSON body and return JSON response
    
    :param method: 'GET' or 'POST'
    :param ip: Target IP address
    :param port: Target port
    :param path: API path (e.g., '/login')
    :param data: Dictionary to send as JSON body
    :return: Parsed JSON response or None on error
    """
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip, int(port)))
        
        # Prepare request
        if method == 'GET':
            request = (
                "GET {} HTTP/1.1\r\n"
                "Host: {}:{}\r\n"
                "Accept: application/json\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(path, ip, port)
        else:  # POST
            body = json.dumps(data) if data else '{}'
            request = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}:{}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
                "{}"
            ).format(path, ip, port, len(body), body)
        
        # Send request
        sock.sendall(request.encode('utf-8'))
        
        # Receive response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        
        sock.close()
        
        # Parse response
        response_str = response.decode('utf-8')
        if '\r\n\r\n' in response_str:
            headers, body = response_str.split('\r\n\r\n', 1)
            try:
                return json.loads(body)
            except:
                return {"status": "error", "message": "Invalid JSON response", "raw": body}
        
        return {"status": "error", "message": "Invalid HTTP response"}
    
    except Exception as e:
        print("ERROR: Request failed - {}".format(str(e)))
        return {"status": "error", "message": str(e)}


def print_response(title, response):
    """Pretty print response"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(json.dumps(response, indent=2))


def main():
    """Interactive chat client demo"""
    print("=" * 70)
    print("HYBRID P2P CHAT CLIENT")
    print("=" * 70)
    print()
    
    # Configuration
    tracker_ip = "127.0.0.1"
    tracker_port = 8000
    
    print("Configuration:")
    print("  Tracker: {}:{}".format(tracker_ip, tracker_port))
    print()
    
    # Step 1: Login
    print("-" * 70)
    print("PHASE 1: CLIENT-SERVER INITIALIZATION")
    print("-" * 70)
    
    username = input("\n[1] Enter username [admin]: ").strip() or "admin"
    password = input("    Enter password [password]: ").strip() or "password"
    
    print("\nLogging in...")
    response = send_json_request('POST', tracker_ip, tracker_port, '/login', {
        'username': username,
        'password': password
    })
    print_response("LOGIN RESPONSE", response)
    
    if response.get('status') != 'success':
        print("\n✗ Login failed. Exiting.")
        return
    
    time.sleep(1)
    
    # Step 2: Register peer
    peer_ip = input("\n[2] Enter your peer IP [127.0.0.1]: ").strip() or "127.0.0.1"
    peer_port = input("    Enter your peer port [7000]: ").strip() or "7000"
    peer_address = "{}:{}".format(peer_ip, peer_port)
    
    print("\nRegistering peer {}...".format(peer_address))
    response = send_json_request('POST', tracker_ip, tracker_port, '/submit-info', {
        'username': username,
        'ip': peer_ip,
        'port': int(peer_port)
    })
    print_response("PEER REGISTRATION RESPONSE", response)
    
    if response.get('status') != 'success':
        print("\n✗ Registration failed. Exiting.")
        return
    
    time.sleep(1)
    
    # Step 3: Get peer list
    print("\n[3] Discovering peers and channels...")
    response = send_json_request('GET', tracker_ip, tracker_port, '/get-list')
    print_response("PEER DISCOVERY RESPONSE", response)
    
    if response.get('status') == 'success':
        peers = response.get('peers', [])
        channels = response.get('channels', {})
        
        print("\nActive Peers:")
        for i, peer in enumerate(peers, 1):
            print("  {}. {} @ {}".format(i, peer.get('username'), peer.get('peer_address')))
        
        print("\nAvailable Channels:")
        for channel_name, channel_info in channels.items():
            members = channel_info.get('members', [])
            print("  - {} ({} members)".format(channel_name, len(members)))
    
    time.sleep(1)
    
    # Step 4: Join or create channel
    channel_name = input("\n[4] Enter channel to join [general]: ").strip() or "general"
    
    print("\nJoining channel '{}'...".format(channel_name))
    response = send_json_request('POST', tracker_ip, tracker_port, '/add-list', {
        'username': username,
        'channel': channel_name,
        'peer_address': peer_address
    })
    print_response("JOIN CHANNEL RESPONSE", response)
    
    if response.get('status') != 'success':
        print("\n✗ Failed to join channel. Exiting.")
        return
    
    channel_members = response.get('members', [])
    print("\nChannel '{}' members:".format(channel_name))
    for member in channel_members:
        print("  - {}".format(member))
    
    time.sleep(1)
    
    # Step 5: P2P Communication
    print("\n" + "-" * 70)
    print("PHASE 2: PEER-TO-PEER COMMUNICATION")
    print("-" * 70)
    
    action = input("\n[5] Choose action:\n"
                   "  1. Broadcast message to channel\n"
                   "  2. Send direct message to peer\n"
                   "  3. Skip\n"
                   "Choice [1]: ").strip() or "1"
    
    if action == "1":
        # Broadcast message
        message = input("\nEnter message to broadcast: ").strip()
        
        if message:
            print("\nBroadcasting to channel '{}'...".format(channel_name))
            
            # Get updated channel members
            response = send_json_request('GET', tracker_ip, tracker_port, '/get-list')
            if response.get('status') == 'success':
                channels = response.get('channels', {})
                members = channels.get(channel_name, {}).get('members', [])
                
                success_count = 0
                for member_address in members:
                    if member_address == peer_address:
                        continue  # Don't send to self
                    
                    # Parse member address
                    member_ip, member_port = member_address.split(':')
                    
                    print("  Sending to {}...".format(member_address))
                    peer_response = send_json_request(
                        'POST',
                        member_ip,
                        member_port,
                        '/broadcast-peer',
                        {
                            'channel': channel_name,
                            'from': peer_address,
                            'username': username,
                            'message': message
                        }
                    )
                    
                    if peer_response.get('status') == 'success':
                        success_count += 1
                        print("    ✓ Delivered")
                    else:
                        print("    ✗ Failed: {}".format(peer_response.get('message', 'Unknown error')))
                
                print("\n✓ Broadcast complete! Delivered to {}/{} peers".format(
                    success_count, len(members) - 1))
    
    elif action == "2":
        # Direct message
        target = input("\nEnter target peer address (ip:port): ").strip()
        message = input("Enter message: ").strip()
        
        if target and message:
            target_ip, target_port = target.split(':')
            
            print("\nSending direct message to {}...".format(target))
            response = send_json_request(
                'POST',
                target_ip,
                target_port,
                '/send-peer',
                {
                    'from': peer_address,
                    'username': username,
                    'message': message
                }
            )
            print_response("DIRECT MESSAGE RESPONSE", response)
            
            if response.get('status') == 'success':
                print("\n✓ Message sent successfully!")
            else:
                print("\n✗ Failed to send message")
    
    # Summary
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nYour peer should be running on: {}".format(peer_address))
    print("\nWhat you can do next:")
    print("  1. Start your peer node: python chat_app.py peer --port {} --username {}".format(
        peer_port, username))
    print("  2. Other peers can send you messages")
    print("  3. Check received messages via GET /get-messages")
    print()


def test_scenario():
    """
    Automated test scenario
    Tests all APIs in sequence
    """
    print("=" * 70)
    print("AUTOMATED TEST SCENARIO")
    print("=" * 70)
    print()
    
    tracker_ip = "127.0.0.1"
    tracker_port = 8000
    
    tests = []
    
    # Test 1: Login
    print("[TEST 1] Login as admin...")
    response = send_json_request('POST', tracker_ip, tracker_port, '/login_app', {
        'username': 'admin',
        'password': 'password'
    })
    tests.append(("Login", response.get('status') == 'success'))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    time.sleep(0.5)
    
    # Test 2: Register peer 1
    print("\n[TEST 2] Register peer 1 (127.0.0.1:7000)...")
    response = send_json_request('POST', tracker_ip, tracker_port, '/submit-info', {
        'username': 'admin',
        'ip': '127.0.0.1',
        'port': 7000
    })
    tests.append(("Register Peer 1", response.get('status') == 'success'))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    time.sleep(0.5)
    
    # Test 3: Register peer 2
    print("\n[TEST 3] Login and register peer 2 (127.0.0.1:7001)...")
    send_json_request('POST', tracker_ip, tracker_port, '/login_app', {
        'username': 'user1',
        'password': 'pass1'
    })
    response = send_json_request('POST', tracker_ip, tracker_port, '/submit-info', {
        'username': 'user1',
        'ip': '127.0.0.1',
        'port': 7001
    })
    tests.append(("Register Peer 2", response.get('status') == 'success'))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    time.sleep(0.5)
    
    # Test 4: Get peer list
    print("\n[TEST 4] Get peer list...")
    response = send_json_request('GET', tracker_ip, tracker_port, '/get-list')
    tests.append(("Get Peer List", response.get('status') == 'success' and len(response.get('peers', [])) >= 2))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    if tests[-1][1]:
        print("  Found {} peers".format(len(response.get('peers', []))))
    time.sleep(0.5)
    
    # Test 5: Create channel
    print("\n[TEST 5] Peer 1 joins channel 'general'...")
    response = send_json_request('POST', tracker_ip, tracker_port, '/add-list', {
        'username': 'admin',
        'channel': 'general',
        'peer_address': '127.0.0.1:7000'
    })
    tests.append(("Join Channel Peer 1", response.get('status') == 'success'))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    time.sleep(0.5)
    
    # Test 6: Join channel
    print("\n[TEST 6] Peer 2 joins channel 'general'...")
    response = send_json_request('POST', tracker_ip, tracker_port, '/add-list', {
        'username': 'user1',
        'channel': 'general',
        'peer_address': '127.0.0.1:7001'
    })
    tests.append(("Join Channel Peer 2", response.get('status') == 'success'))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    if tests[-1][1]:
        print("  Channel has {} members".format(response.get('member_count', 0)))
    time.sleep(0.5)
    
    # Test 7: Connect to peer
    print("\n[TEST 7] Get connection info for peer 2...")
    response = send_json_request('POST', tracker_ip, tracker_port, '/connect-peer', {
        'peer_address': '127.0.0.1:7001'
    })
    tests.append(("Connect Peer", response.get('status') == 'success'))
    print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    time.sleep(0.5)
    
    # Test 8: P2P message (requires peer nodes running)
    print("\n[TEST 8] Send P2P message (requires peer nodes running)...")
    try:
        response = send_json_request('POST', '127.0.0.1', 7001, '/broadcast-peer', {
            'channel': 'general',
            'from': '127.0.0.1:7000',
            'username': 'admin',
            'message': 'Test message from automated script'
        })
        tests.append(("P2P Broadcast", response.get('status') == 'success'))
        print("Result: {}".format("✓ PASS" if tests[-1][1] else "✗ FAIL"))
    except:
        tests.append(("P2P Broadcast", False))
        print("Result: ✗ FAIL (Peer node not running)")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "✓ PASS" if result else "✗ FAIL"
        print("  {} - {}".format(status, name))
    
    print("\n  Total: {}/{} tests passed ({:.1f}%)".format(
        passed, total, (passed/total * 100) if total > 0 else 0))
    print("=" * 70)
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_scenario()
    else:
        main()