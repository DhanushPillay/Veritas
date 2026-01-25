/**
 * Veritas Chatbot - Frontend JavaScript
 * Handles chat interactions, conversation management, and UI
 */

// ========== STATE ==========
const state = {
  currentConversationId: null,
  isLoading: false,
  conversations: []
};

// ========== DOM ELEMENTS ==========
const elements = {
  chatForm: document.getElementById('chatForm'),
  messageInput: document.getElementById('messageInput'),
  sendBtn: document.getElementById('sendBtn'),
  messagesContainer: document.getElementById('messagesContainer'),
  welcomeScreen: document.getElementById('welcomeScreen'),
  conversationList: document.getElementById('conversationList'),
  newChatBtn: document.getElementById('newChatBtn'),
  clearAllBtn: document.getElementById('clearAllBtn'),
  sidebar: document.getElementById('sidebar'),
  sidebarToggle: document.getElementById('sidebarToggle'),
  chatContainer: document.getElementById('chatContainer')
};

// ========== API ==========
const API_BASE = '/api';

async function sendMessage(message, conversationId = null) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      stream: false
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to send message');
  }

  return response.json();
}

async function getConversations() {
  const response = await fetch(`${API_BASE}/conversations`);
  const data = await response.json();
  return data.conversations || [];
}

async function getConversation(id) {
  const response = await fetch(`${API_BASE}/conversations/${id}`);
  return response.json();
}

async function deleteConversation(id) {
  await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
}

async function clearAllConversations() {
  await fetch(`${API_BASE}/conversations`, { method: 'DELETE' });
}

// ========== UI HELPERS ==========

function showWelcome() {
  elements.welcomeScreen.classList.remove('hidden');
  elements.messagesContainer.classList.remove('active');
}

function hideWelcome() {
  elements.welcomeScreen.classList.add('hidden');
  elements.messagesContainer.classList.add('active');
}

function scrollToBottom() {
  elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

function renderMarkdown(text) {
  // Configure marked for safe rendering
  marked.setOptions({
    breaks: true,
    gfm: true
  });
  return marked.parse(text);
}

function addMessage(role, content, isStreaming = false) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  const avatar = role === 'user' ? 'U' : 'V';

  messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">${avatar}</div>
            <div class="message-text">
                ${isStreaming ? '<div class="typing-indicator"><span></span><span></span><span></span></div>' : renderMarkdown(content)}
            </div>
        </div>
    `;

  elements.messagesContainer.appendChild(messageDiv);
  scrollToBottom();

  return messageDiv;
}

function updateMessage(messageDiv, content) {
  const textElement = messageDiv.querySelector('.message-text');
  textElement.innerHTML = renderMarkdown(content);
  scrollToBottom();
}

function updateSendButton() {
  const hasText = elements.messageInput.value.trim().length > 0;
  elements.sendBtn.disabled = !hasText || state.isLoading;
}

function autoResizeTextarea() {
  elements.messageInput.style.height = 'auto';
  elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 200) + 'px';
}

// ========== CONVERSATION MANAGEMENT ==========

function renderConversationList() {
  elements.conversationList.innerHTML = '';

  state.conversations.forEach(conv => {
    const item = document.createElement('button');
    item.className = `conversation-item ${conv.id === state.currentConversationId ? 'active' : ''}`;
    item.innerHTML = `
            <span class="conversation-title">${escapeHtml(conv.title)}</span>
            <button class="conversation-delete" title="Delete">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;

    // Click to load conversation
    item.addEventListener('click', (e) => {
      if (!e.target.closest('.conversation-delete')) {
        loadConversation(conv.id);
      }
    });

    // Delete button
    item.querySelector('.conversation-delete').addEventListener('click', async (e) => {
      e.stopPropagation();
      await deleteConversation(conv.id);
      await refreshConversations();

      if (state.currentConversationId === conv.id) {
        startNewChat();
      }
    });

    elements.conversationList.appendChild(item);
  });
}

async function refreshConversations() {
  state.conversations = await getConversations();
  renderConversationList();
}

async function loadConversation(id) {
  const conversation = await getConversation(id);
  state.currentConversationId = id;

  // Clear messages
  elements.messagesContainer.innerHTML = '';
  hideWelcome();

  // Render all messages
  conversation.messages.forEach(msg => {
    addMessage(msg.role, msg.content);
  });

  renderConversationList();
  closeSidebar();
}

function startNewChat() {
  state.currentConversationId = null;
  elements.messagesContainer.innerHTML = '';
  showWelcome();
  renderConversationList();
  elements.messageInput.focus();
}

// ========== CHAT HANDLING ==========

async function handleSubmit(e) {
  e.preventDefault();

  const message = elements.messageInput.value.trim();
  if (!message || state.isLoading) return;

  // Clear input
  elements.messageInput.value = '';
  autoResizeTextarea();
  updateSendButton();

  // Hide welcome, show chat
  hideWelcome();

  // Add user message
  addMessage('user', message);

  // Add loading indicator
  const assistantMessage = addMessage('assistant', '', true);

  state.isLoading = true;
  updateSendButton();

  try {
    const response = await sendMessage(message, state.currentConversationId);

    // Update conversation ID if new
    if (!state.currentConversationId) {
      state.currentConversationId = response.conversation_id;
    }

    // Update message with response
    updateMessage(assistantMessage, response.response);

    // Refresh conversation list
    await refreshConversations();

  } catch (error) {
    updateMessage(assistantMessage, `**Error:** ${error.message}`);
  } finally {
    state.isLoading = false;
    updateSendButton();
  }
}

// ========== SIDEBAR MOBILE ==========

function toggleSidebar() {
  elements.sidebar.classList.toggle('open');
}

function closeSidebar() {
  elements.sidebar.classList.remove('open');
}

// ========== UTILS ==========

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ========== EVENT LISTENERS ==========

// Form submit
elements.chatForm.addEventListener('submit', handleSubmit);

// Input changes
elements.messageInput.addEventListener('input', () => {
  updateSendButton();
  autoResizeTextarea();
});

// Enter to send (Shift+Enter for new line)
elements.messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    elements.chatForm.dispatchEvent(new Event('submit'));
  }
});

// New chat button
elements.newChatBtn.addEventListener('click', () => {
  startNewChat();
  closeSidebar();
});

// Clear all button
elements.clearAllBtn.addEventListener('click', async () => {
  if (confirm('Are you sure you want to delete all conversations?')) {
    await clearAllConversations();
    await refreshConversations();
    startNewChat();
  }
});

// Sidebar toggle
elements.sidebarToggle.addEventListener('click', toggleSidebar);

// Suggestion cards
document.querySelectorAll('.suggestion-card').forEach(card => {
  card.addEventListener('click', () => {
    const prompt = card.dataset.prompt;
    elements.messageInput.value = prompt;
    autoResizeTextarea();
    updateSendButton();
    elements.messageInput.focus();
  });
});

// Close sidebar when clicking outside (mobile)
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768) {
    if (!elements.sidebar.contains(e.target) && !elements.sidebarToggle.contains(e.target)) {
      closeSidebar();
    }
  }
});

// ========== INIT ==========

async function init() {
  await refreshConversations();
  elements.messageInput.focus();
}

init();
