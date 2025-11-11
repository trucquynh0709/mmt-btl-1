// Configuration
const config = {
  trackerUrl: 'http://127.0.0.1:8000',
  username: '',
  peerIp: '',
  peerPort: 0,
  peerAddress: '',
  loggedIn: false,
  registered: false,
  currentChannel: 'general',
  channels: {},
  lastMessageCount: {},
  selectedDirectPeer: '',
  directMessages: {},
  lastDirectMessageCount: {}
};

// Switch between tabs
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));

  event.target.classList.add('active');
  document.getElementById(tab + '-content').classList.add('active');

  if (tab === 'chat') {
    loadMessages(config.currentChannel);
  } else if (tab === 'peers') {
    discoverPeers();
  }
}

// Step 1: Login
async function login() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;

  if (!username || !password) {
    alert('Please enter username and password');
    return;
  }

  try {
    const response = await fetch(`${config.trackerUrl}/login_app`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (data.status === 'success') {
      config.username = username;
      config.loggedIn = true;

      updateStatus('Logged in as ' + username);
      document.getElementById('register-btn').disabled = false;
      showNotification('Login Successful', `Welcome, ${username}!`);
    } else {
      alert('Login failed: ' + data.message);
    }
  } catch (error) {
    alert('Login error: ' + error.message);
  }
}

// Step 2: Register Peer
async function registerPeer() {
  const peerIp = document.getElementById('peer-ip').value;
  const peerPort = parseInt(document.getElementById('peer-port').value);

  if (!peerIp || !peerPort) {
    alert('Please enter peer IP and port');
    return;
  }

  try {
    const response = await fetch(`${config.trackerUrl}/submit-info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: config.username,
        ip: peerIp,
        port: peerPort
      })
    });

    const data = await response.json();

    if (data.status === 'success') {
      config.peerIp = peerIp;
      config.peerPort = peerPort;
      config.peerAddress = `${peerIp}:${peerPort}`;
      config.registered = true;

      document.getElementById('peer-info').textContent =
        `${config.username} @ ${config.peerAddress}`;
      updateStatus('Peer registered at ' + config.peerAddress);
      document.getElementById('join-btn').disabled = false;
      showNotification('Peer Registered', `Address: ${config.peerAddress}`);
    } else {
      alert('Registration failed: ' + data.message);
    }
  } catch (error) {
    alert('Registration error: ' + error.message);
  }
}

// Step 3: Join Channel
async function joinChannel() {
  const channelName = document.getElementById('channel-name').value;

  if (!channelName) {
    alert('Please enter channel name');
    return;
  }

  try {
    const response = await fetch(`${config.trackerUrl}/add-list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: config.username,
        channel: channelName,
        peer_address: config.peerAddress
      })
    });

    const data = await response.json();

    if (data.status === 'success') {
      if (!config.channels[channelName]) {
        config.channels[channelName] = {
          members: data.members || [],
          unread: 0
        };
        config.lastMessageCount[channelName] = 0;
      }

      updateStatus('Connected - ' + Object.keys(config.channels).length + ' channels');
      updateChannelsList();
      showNotification('Joined Channel', `#${channelName} - ${data.member_count} members`);

      // Step 4: Sync old messages from an existing peer
      const members = data.members || [];
      if (members.length > 0) {
        const [ip, port] = members[0].split(':');
        try {
          const resp = await fetch(`http://${ip}:${port}/get-messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel: channelName })
          });
          const history = await resp.json();

          if (history.status === 'success') {
            console.log(`Fetched ${history.message_count} messages from ${members[0]}`);

            // Step 5: Locally broadcast history to our own peer backend
            await fetch(`http://${config.peerIp}:${config.peerPort}/broadcast-peer`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                from: config.peerAddress,
                username: config.username,
                channel: channelName,
                messages: history.messages,
                sync: true
              })
            });

            // Update UI
            displayMessages(history.messages);
            config.channels[channelName].messages = history.messages;
          }
        } catch (err) {
          console.warn('Could not fetch channel history from', members[0], err);
        }
      }

      // Start polling for new messages
      startMessagePolling();
    } else {
      alert('Failed to join channel: ' + data.message);
    }
  } catch (error) {
    alert('Join channel error: ' + error.message);
  }
}

// Update channels list
function updateChannelsList() {
  const container = document.getElementById('channels-list');
  container.innerHTML = '';

  for (const [name, data] of Object.entries(config.channels)) {
    const div = document.createElement('div');
    div.className = 'channel';
    if (name === config.currentChannel) {
      div.classList.add('active');
    }

    let badge = '';
    if (data.unread > 0) {
      badge = `<span class="badge">${data.unread}</span>`;
    }

    div.innerHTML = `#${name}${badge}`;
    div.onclick = () => selectChannel(name);
    container.appendChild(div);
  }
}

// Select channel
function selectChannel(channelName) {
  config.currentChannel = channelName;
  config.channels[channelName].unread = 0;
  updateChannelsList();
  loadMessages(channelName);
}

// Load messages from peer node
async function loadMessages(channelName) {
  try {
    const response = await fetch(`http://${config.peerIp}:${config.peerPort}/get-messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel: channelName })
    });

    const data = await response.json();

    if (data.status === 'success') {
      displayMessages(data.messages);
    }
  } catch (error) {
    console.error('Failed to load messages:', error);
  }
}

// Display messages
function displayMessages(messages) {
  const container = document.getElementById('messages');
  container.innerHTML = '';

  if (messages.length === 0) {
    container.innerHTML = '<div class="empty-state">No messages yet. Start chatting!</div>';
    return;
  }

  messages.forEach(msg => {
    const div = document.createElement('div');
    div.className = 'message';
    if (msg.username === config.username) {
      div.classList.add('own');
    }

    const time = new Date(msg.timestamp).toLocaleTimeString();

    div.innerHTML = `
                    <div class="meta">
                        <span class="username">${msg.username}</span>
                        <span>${time}</span>
                    </div>
                    <div class="text">${escapeHtml(msg.message)}</div>
                `;

    container.appendChild(div);
  });

  container.scrollTop = container.scrollHeight;
}

// Send message
async function sendMessage() {
  const input = document.getElementById('message-input');
  const message = input.value.trim();

  if (!message) return;

  try {
    // Get channel members
    const response = await fetch(`${config.trackerUrl}/get-list`);
    const data = await response.json();

    if (data.status === 'success') {
      const members = data.channels[config.currentChannel]?.members || [];

      // Send to own peer first (so we can see our own messages)
      await fetch(`http://${config.peerIp}:${config.peerPort}/broadcast-peer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: config.currentChannel,
          from: config.peerAddress,
          username: config.username,
          message: message
        })
      });

      // Broadcast to all other members
      for (const memberAddress of members) {
        if (memberAddress === config.peerAddress) continue;

        const [ip, port] = memberAddress.split(':');

        await fetch(`http://${ip}:${port}/broadcast-peer`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            channel: config.currentChannel,
            from: config.peerAddress,
            username: config.username,
            message: message
          })
        }).catch(err => console.error(`Failed to send to ${memberAddress}:`, err));
      }

      input.value = '';
      loadMessages(config.currentChannel);
    }
  } catch (error) {
    alert('Failed to send message: ' + error.message);
  }
}

// Handle Enter key
function handleKeyPress(event) {
  if (event.key === 'Enter') {
    sendMessage();
  }
}

// Discover peers
async function discoverPeers() {
  const cacheKey = 'peer_data_cache';

  try {
    const response = await fetch(`${config.trackerUrl}/get-list`);
    const data = await response.json();

    if (data.status === 'success') {
      // ✅ Update UI and lists
      displayPeers(data.peers);
      updateDirectPeerList(data.peers);

      // ✅ Save latest peers + channels to localStorage for fallback use
      localStorage.setItem(cacheKey, JSON.stringify({
        timestamp: new Date().toISOString(),
        peers: data.peers,
        channels: data.channels
      }));

      console.log('[Cache] Peer data saved to localStorage');
    } else {
      throw new Error('Tracker returned error: ' + data.message);
    }

  } catch (error) {
    console.warn('[DiscoverPeers] Tracker unavailable, using cached data:', error.message);

    // ✅ Attempt to load from localStorage cache
    const cachedData = localStorage.getItem(cacheKey);
    if (cachedData) {
      const parsed = JSON.parse(cachedData);
      console.log('[Cache] Loaded peers from localStorage, timestamp:', parsed.timestamp);

      displayPeers(parsed.peers);
      updateDirectPeerList(parsed.peers);

      showNotification('Tracking server is down', 'Using cached peer list from last sync.');
    } else {
      console.error('[Cache] No cached peer data available.');
      alert('Failed to fetch peers and no cache found.');
    }
  }
}


// Display peers
function displayPeers(peers) {
  const container = document.getElementById('peer-list');
  container.innerHTML = '';

  if (peers.length === 0) {
    container.innerHTML = '<div class="empty-state">No active peers</div>';
    return;
  }

  peers.forEach(peer => {
    const div = document.createElement('div');
    div.className = 'peer-item';
    const isSelf = peer.peer_address === config.peerAddress ? ' (You)' : '';
    div.innerHTML = `
                    <div class="name">${peer.username}${isSelf}</div>
                    <div class="address">${peer.peer_address}</div>
                `;
    container.appendChild(div);
  });
}

// Update direct message peer list
function updateDirectPeerList(peers) {
  const select = document.getElementById('direct-peer-select');
  const currentValue = select.value;

  select.innerHTML = '<option value="">-- Select a peer --</option>';

  peers.forEach(peer => {
    if (peer.peer_address !== config.peerAddress) {
      const option = document.createElement('option');
      option.value = peer.peer_address;
      option.textContent = `${peer.username} (${peer.peer_address})`;
      select.appendChild(option);
    }
  });

  // Restore selection
  if (currentValue) {
    select.value = currentValue;
  }

  // Listen for selection changes
  select.onchange = function () {
    config.selectedDirectPeer = this.value;
    if (this.value) {
      loadDirectMessages(this.value);
    } else {
      // Clear messages if no peer selected
      document.getElementById('direct-messages').innerHTML =
        '<div class="empty-state">Select a peer to view messages</div>';
    }
  };
}

// Load direct messages
async function loadDirectMessages(peerAddress) {
  if (!peerAddress) return;

  try {
    // Use the new get-peer-messages endpoint
    const response = await fetch(`http://${config.peerIp}:${config.peerPort}/get-peer-messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ peer_address: peerAddress })
    });

    const data = await response.json();

    if (data.status === 'success') {
      displayDirectMessages(data.messages, peerAddress);
      config.lastDirectMessageCount[peerAddress] = data.message_count;
    } else {
      displayDirectMessages([], peerAddress);
    }
  } catch (error) {
    console.error('Failed to load direct messages:', error);
    displayDirectMessages([], peerAddress);
  }
}

// Display direct messages
function displayDirectMessages(messages, peerAddress) {
  const container = document.getElementById('direct-messages');
  container.innerHTML = '';

  if (messages.length === 0) {
    container.innerHTML = '<div class="empty-state">No direct messages yet. Send one!</div>';
    return;
  }

  messages.forEach(msg => {
    const div = document.createElement('div');
    div.className = 'message';

    // If message is FROM us (our peerAddress), show on right (own)
    // If message is FROM the other peer, show on left
    const isFromUs = msg.from === config.peerAddress;

    if (isFromUs) {
      div.classList.add('own');
    }

    const time = new Date(msg.timestamp).toLocaleTimeString();

    div.innerHTML = `
                    <div class="meta">
                        <span class="username">${msg.username}</span>
                        <span>${time}</span>
                    </div>
                    <div class="text">${escapeHtml(msg.message)}</div>
                `;

    container.appendChild(div);
  });

  container.scrollTop = container.scrollHeight;
}
// Send direct message
async function sendDirectMessage() {
  const input = document.getElementById('direct-message-input');
  const message = input.value.trim();
  const targetPeer = config.selectedDirectPeer;

  if (!message) {
    alert('Please enter a message');
    return;
  }

  if (!targetPeer) {
    alert('Please select a peer');
    return;
  }

  try {
    const [targetIp, targetPort] = targetPeer.split(':');

    // Step 1: Save to OUR peer (so we see our sent message)
    await fetch(`http://${config.peerIp}:${config.peerPort}/send-peer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: config.peerAddress,
        username: config.username,
        message: message,
        to: targetPeer
      })
    });

    // Step 2: Send to TARGET peer (so they receive it)
    await fetch(`http://${targetIp}:${targetPort}/send-peer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: config.peerAddress,
        username: config.username,
        message: message
      })
    }).catch(err => {
      console.error(`Failed to send to ${targetPeer}:`, err);
      showNotification('Warning', `Saved locally but failed to deliver to ${targetPeer}`);
    });

    input.value = '';
    loadDirectMessages(targetPeer);  // Reload to show sent message
    showNotification('Direct Message Sent', `To: ${targetPeer}`);

  } catch (error) {
    alert('Failed to send direct message: ' + error.message);
  }
}

// Handle Enter key for direct messages
function handleDirectKeyPress(event) {
  if (event.key === 'Enter') {
    sendDirectMessage();
  }
}

// Start polling for new messages
function startMessagePolling() {
  // Poll every 2 seconds
  setInterval(async () => {
    // ==========================================
    // Poll channel messages
    // ==========================================
    for (const channelName of Object.keys(config.channels)) {
      try {
        const response = await fetch(`http://${config.peerIp}:${config.peerPort}/get-messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channel: channelName })
        });

        const data = await response.json();

        if (data.status === 'success') {
          const currentCount = data.messages.length;
          const lastCount = config.lastMessageCount[channelName] || 0;

          if (currentCount > lastCount) {
            const newMessages = currentCount - lastCount;

            // Show notification for new messages
            if (channelName !== config.currentChannel) {
              config.channels[channelName].unread += newMessages;
              updateChannelsList();
            }

            // Get the latest message
            const latestMsg = data.messages[data.messages.length - 1];
            if (latestMsg && latestMsg.username !== config.username) {
              showNotification(
                `New message in #${channelName}`,
                `${latestMsg.username}: ${latestMsg.message.substring(0, 50)}${latestMsg.message.length > 50 ? '...' : ''}`
              );
            }

            // Reload if viewing this channel
            if (channelName === config.currentChannel) {
              displayMessages(data.messages);
            }
          }

          config.lastMessageCount[channelName] = currentCount;
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }

    // ==========================================
    // Poll direct messages 
    // ==========================================
    if (config.selectedDirectPeer) {
      try {
        const response = await fetch(`http://${config.peerIp}:${config.peerPort}/get-peer-messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ peer_address: config.selectedDirectPeer })
        });

        const data = await response.json();

        if (data.status === 'success') {
          const currentCount = data.message_count;
          const lastCount = config.lastDirectMessageCount[config.selectedDirectPeer] || 0;

          if (currentCount > lastCount) {
            // New messages arrived
            const newMessages = currentCount - lastCount;

            // Get the latest message
            const latestMsg = data.messages[data.messages.length - 1];

            // Only notify if the message is FROM the other peer (not from us)
            if (latestMsg && latestMsg.from === config.selectedDirectPeer) {
              showNotification(
                'New Direct Message',
                `${latestMsg.username}: ${latestMsg.message.substring(0, 50)}${latestMsg.message.length > 50 ? '...' : ''}`
              );
            }

            // Reload to show new messages
            displayDirectMessages(data.messages, config.selectedDirectPeer);
          }

          config.lastDirectMessageCount[config.selectedDirectPeer] = currentCount;
        }
      } catch (error) {
        console.error('Direct message polling error:', error);
      }
    }

  }, 2000); // Poll every 2 seconds

  // ==========================================
  // Send heartbeat to tracker every 30 seconds
  // ==========================================
  setInterval(async () => {
    if (config.registered) {
      try {
        await fetch(`${config.trackerUrl}/submit-info`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: config.username,
            ip: config.peerIp,
            port: config.peerPort
          })
        });
        console.log('[Heartbeat] Sent to tracker');
      } catch (error) {
        console.error('[Heartbeat] Failed:', error);
      }
    }
  }, 30000); // Every 30 seconds
}

// Show notification
function showNotification(title, message) {
  const notif = document.createElement('div');
  notif.className = 'notification';
  notif.innerHTML = `
                <div class="title">${title}</div>
                <div class="message">${message}</div>
            `;

  document.body.appendChild(notif);

  setTimeout(() => {
    notif.classList.add('hide');
    setTimeout(() => notif.remove(), 300);
  }, 3000);
}

// Update status
function updateStatus(text) {
  const status = document.getElementById('status');
  status.textContent = text;
  status.classList.remove('offline');
}

// Escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}