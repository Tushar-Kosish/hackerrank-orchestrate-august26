/**
 * WhatsApp Message Notification Router Dashboard Client
 */
document.addEventListener('DOMContentLoaded', () => {
  let datasetMessages = [];
  let currentFilter = 'all';

  // DOM Elements
  const menuBtn = document.getElementById('menuBtn');
  const closeSidebar = document.getElementById('closeSidebar');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const refreshBtn = document.getElementById('refreshBtn');
  const liveClock = document.getElementById('liveClock');

  const valTotal = document.getElementById('valTotal');
  const valNotify = document.getElementById('valNotify');
  const valDigest = document.getElementById('valDigest');
  const valMute = document.getElementById('valMute');

  const messagesTbody = document.getElementById('messagesTbody');
  const cardsFeed = document.getElementById('cardsFeed');
  const tableSearch = document.getElementById('tableSearch');
  const filterTabs = document.querySelectorAll('.tab-btn');

  const simForm = document.getElementById('simForm');
  const msgText = document.getElementById('msgText');
  const convType = document.getElementById('convType');
  const mediaType = document.getElementById('mediaType');
  const forwardedCount = document.getElementById('forwardedCount');
  const senderId = document.getElementById('senderId');
  const resetSimBtn = document.getElementById('resetSimBtn');

  const simResult = document.getElementById('simResult');
  const resActionTag = document.getElementById('resActionTag');
  const resCategory = document.getElementById('resCategory');
  const resReason = document.getElementById('resReason');
  const resConfBar = document.getElementById('resConfBar');
  const resConfNum = document.getElementById('resConfNum');
  const resEvidence = document.getElementById('resEvidence');

  // --- Clock Update ---
  function updateClock() {
    const now = new Date();
    liveClock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // --- Mobile Navigation Drawer Toggle ---
  function openNav() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('active');
  }

  function closeNav() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
  }

  if (menuBtn) menuBtn.addEventListener('click', openNav);
  if (closeSidebar) closeSidebar.addEventListener('click', closeNav);
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeNav);

  // --- Fetch Dataset ---
  async function fetchDataset() {
    try {
      const res = await fetch('/api/dataset');
      if (!res.ok) throw new Error('Failed to load dataset API');
      const data = await res.json();
      datasetMessages = data.messages || [];

      // Update Stat Cards
      if (valTotal) valTotal.textContent = data.stats.total || datasetMessages.length;
      if (valNotify) valNotify.textContent = data.stats.notify || 0;
      if (valDigest) valDigest.textContent = data.stats.digest || 0;
      if (valMute) valMute.textContent = data.stats.mute || 0;

      renderMessages();
    } catch (err) {
      console.error('Error loading dataset:', err);
    }
  }

  // --- Render Messages (Table & Mobile Cards) ---
  function renderMessages() {
    const query = tableSearch.value.trim().toLowerCase();

    const filtered = datasetMessages.filter(msg => {
      const matchesFilter = currentFilter === 'all' || (msg.action || '').toLowerCase() === currentFilter;
      const textMatch = (msg.message_text || '').toLowerCase().includes(query) ||
                        (msg.message_id || '').toLowerCase().includes(query) ||
                        (msg.sender_user_id || '').toLowerCase().includes(query);
      return matchesFilter && textMatch;
    });

    // Render Table Rows (Desktop)
    messagesTbody.innerHTML = filtered.map(msg => {
      const action = (msg.action || 'digest').toLowerCase();
      const actionBadge = `<span class="action-tag ${action}">${action}</span>`;
      const confPercent = Math.round((msg.confidence || 0.3) * 100);
      const chatReply = msg.chat_reply || '';

      return `
        <tr data-id="${msg.message_id}">
          <td class="code-font">${msg.message_id || ''}</td>
          <td>
            <strong>${msg.sender_user_id || msg.user_id || 'Unknown'}</strong>
            <br><span style="font-size: 0.75rem; color: var(--text-muted);">${msg.conversation_type || 'personal'}</span>
          </td>
          <td class="msg-text-snippet" title="${msg.message_text || ''}">
            ${msg.message_text || '<em>(No text)</em>'}
          </td>
          <td><span class="code-font">${msg.media_type || 'none'}</span></td>
          <td>${actionBadge}</td>
          <td>
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <div style="width:50px; height:6px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                <div style="width:${confPercent}%; height:100%; background:var(--primary-emerald);"></div>
              </div>
              <span style="font-size:0.75rem;">${confPercent}%</span>
            </div>
          </td>
          <td class="chat-reply-cell" title="${chatReply}">
            ${chatReply ? `<span class="chat-reply-bubble">${chatReply}</span>` : '<em style="color:var(--text-muted);font-size:0.75rem;">—</em>'}
          </td>
        </tr>
      `;
    }).join('');

    // Render Mobile Cards Feed (Mobile/Tablet)
    cardsFeed.innerHTML = filtered.map(msg => {
      const action = (msg.action || 'digest').toLowerCase();
      const confPercent = Math.round((msg.confidence || 0.3) * 100);
      const chatReply = msg.chat_reply || '';

      return `
        <div class="msg-mobile-card" data-id="${msg.message_id}">
          <div class="msg-card-top">
            <span class="code-font">${msg.message_id}</span>
            <span class="action-tag ${action}">${action}</span>
          </div>
          <div style="font-size: 0.9rem; font-weight: 500; margin: 0.2rem 0;">
            ${msg.message_text || '<em>(No text content)</em>'}
          </div>
          ${chatReply ? `<div class="chat-reply-bubble" style="margin-top:0.3rem;">${chatReply}</div>` : ''}
          <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted); margin-top:0.3rem;">
            <span>Sender: ${msg.sender_user_id || msg.user_id} (${msg.conversation_type})</span>
            <span>Conf: ${confPercent}%</span>
          </div>
        </div>
      `;
    }).join('');

    // Click handler to populate simulation form
    document.querySelectorAll('[data-id]').forEach(elem => {
      elem.addEventListener('click', () => {
        const id = elem.getAttribute('data-id');
        const item = datasetMessages.find(m => m.message_id === id);
        if (item) {
          msgText.value = item.message_text || '';
          convType.value = item.conversation_type || 'personal';
          mediaType.value = item.media_type || '';
          forwardedCount.value = item.forwarded_count || 0;
          senderId.value = item.sender_user_id || 's1';
          evaluateRouting();
        }
      });
    });
  }

  // --- Filter Tabs Event Listeners ---
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentFilter = tab.getAttribute('data-filter');
      renderMessages();
    });
  });

  if (tableSearch) tableSearch.addEventListener('input', renderMessages);
  if (refreshBtn) refreshBtn.addEventListener('click', fetchDataset);

  // --- Simulation Form Submission ---
  async function evaluateRouting() {
    const payload = {
      message_id: 'test_sim_' + Date.now(),
      user_id: 'u1',
      conversation_type: convType.value,
      group_id: '',
      business_id: convType.value === 'business' ? 'b1' : '',
      sender_user_id: senderId.value || 's1',
      created_at: new Date().toISOString(),
      message_text: msgText.value,
      media_type: mediaType.value,
      media_id: mediaType.value ? 'media_test_1' : '',
      forwarded_count: parseInt(forwardedCount.value || '0', 10),
    };

    try {
      const res = await fetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      // Show result
      simResult.style.display = 'block';
      const action = (data.action || 'digest').toLowerCase();
      resActionTag.textContent = action.toUpperCase();
      resActionTag.className = `action-tag ${action}`;

      resCategory.textContent = data.message_type || 'unknown';
      resReason.textContent = data.reason || 'None provided';
      const confVal = Math.round((data.confidence || 0.3) * 100);
      resConfBar.style.width = `${confVal}%`;
      resConfNum.textContent = `${confVal}%`;
      resEvidence.textContent = data.evidence_message_ids || 'none';

      // Show chat reply
      const resChatReply = document.getElementById('resChatReply');
      if (resChatReply) {
        resChatReply.textContent = data.chat_reply || '(no reply — muted)';
        resChatReply.style.opacity = data.chat_reply ? '1' : '0.5';
      }
    } catch (err) {
      console.error('Error evaluating route:', err);
    }
  }

  if (simForm) {
    simForm.addEventListener('submit', (e) => {
      e.preventDefault();
      evaluateRouting();
    });
  }

  if (resetSimBtn) {
    resetSimBtn.addEventListener('click', () => {
      simForm.reset();
      simResult.style.display = 'none';
    });
  }

  // Initial fetch
  fetchDataset();
});
