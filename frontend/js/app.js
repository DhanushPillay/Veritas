/**
 * Veritas Chatbot - Frontend JavaScript
 * Handles chat interactions, conversation management, and UI
 */

// ========== STATE ==========
const state = {
  currentConversationId: null,
  isLoading: false,
  conversations: [],
  abortController: null  // For stopping generation
};

// ========== DOM ELEMENTS ==========
const elements = {
  chatForm: document.getElementById('chatForm'),
  messageInput: document.getElementById('messageInput'),
  sendBtn: document.getElementById('sendBtn'),
  stopBtn: document.getElementById('stopBtn'),
  messagesContainer: document.getElementById('messagesContainer'),
  welcomeScreen: document.getElementById('welcomeScreen'),
  conversationList: document.getElementById('conversationList'),
  newChatBtn: document.getElementById('newChatBtn'),
  clearAllBtn: document.getElementById('clearAllBtn'),
  sidebar: document.getElementById('sidebar'),
  sidebarToggle: document.getElementById('sidebarToggle'),
  chatContainer: document.getElementById('chatContainer'),
  themeToggle: document.getElementById('themeToggle')
};

// ========== API ==========
const API_BASE = '/api';

// Streaming message sender
async function sendMessageStream(message, conversationId, onChunk, onDone, signal) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      stream: true
    }),
    signal
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to send message');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullResponse = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.content) {
            fullResponse += data.content;
            onChunk(fullResponse);
          }
          if (data.done) {
            onDone(data.conversation_id);
          }
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }
  }

  return fullResponse;
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

// ========== THEME ==========

function initTheme() {
  const savedTheme = localStorage.getItem('veritas-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('veritas-theme', newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  if (elements.themeToggle) {
    const icon = elements.themeToggle.querySelector('svg');
    if (theme === 'dark') {
      icon.innerHTML = '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>';
    } else {
      icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    }
  }
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
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value;
        } catch (e) { }
      }
      return hljs.highlightAuto(code).value;
    }
  });

  let html = marked.parse(text);

  // Add copy buttons to code blocks
  html = html.replace(/<pre><code([^>]*)>/g, (match, attrs) => {
    const langMatch = attrs.match(/class="language-(\w+)"/);
    const lang = langMatch ? langMatch[1] : 'code';
    return `<div class="code-block"><div class="code-header"><span class="code-lang">${lang}</span><button class="copy-btn" onclick="copyCode(this)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button></div><pre><code${attrs}>`;
  });
  html = html.replace(/<\/code><\/pre>/g, '</code></pre></div>');

  return html;
}

// Global copy function
window.copyCode = function (btn) {
  const codeBlock = btn.closest('.code-block').querySelector('code');
  const text = codeBlock.textContent;

  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20,6 9,17 4,12"/></svg>Copied!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.classList.remove('copied');
    }, 2000);
  });
};

function addMessage(role, content, isStreaming = false) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  messageDiv.dataset.role = role;

  const avatar = role === 'user' ? 'U' : 'V';

  // User messages get edit button, assistant messages get copy/regenerate
  const userActionsHtml = `
        <div class="message-actions">
            <button class="action-btn edit-message-btn" title="Edit message">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
            </button>
        </div>
    `;

  const assistantActionsHtml = `
        <div class="message-actions">
            <button class="action-btn copy-message-btn" title="Copy message">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
            </button>
            <button class="action-btn regenerate-btn" title="Regenerate response">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 4v6h-6M1 20v-6h6"/>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
            </button>
        </div>
    `;

  const actionsHtml = role === 'user' ? userActionsHtml : assistantActionsHtml;

  messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">${avatar}</div>
            <div class="message-body">
                <div class="message-text">
                    ${isStreaming ? '<div class="typing-indicator"><span></span><span></span><span></span></div>' : renderMarkdown(content)}
                </div>
                ${actionsHtml}
            </div>
        </div>
    `;

  // Add event listeners for actions
  const copyBtn = messageDiv.querySelector('.copy-message-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => copyMessageContent(messageDiv));
  }

  const regenBtn = messageDiv.querySelector('.regenerate-btn');
  if (regenBtn) {
    regenBtn.addEventListener('click', () => regenerateResponse(messageDiv));
  }

  const editBtn = messageDiv.querySelector('.edit-message-btn');
  if (editBtn) {
    editBtn.addEventListener('click', () => editMessage(messageDiv));
  }

  elements.messagesContainer.appendChild(messageDiv);
  scrollToBottom();

  return messageDiv;
}

function updateMessage(messageDiv, content) {
  const textElement = messageDiv.querySelector('.message-text');
  textElement.innerHTML = renderMarkdown(content);

  // Re-highlight code blocks
  messageDiv.querySelectorAll('pre code').forEach(block => {
    hljs.highlightElement(block);
  });

  scrollToBottom();
}

function copyMessageContent(messageDiv) {
  const textElement = messageDiv.querySelector('.message-text');
  const text = textElement.textContent;
  navigator.clipboard.writeText(text);

  const btn = messageDiv.querySelector('.copy-message-btn');
  btn.classList.add('copied');
  setTimeout(() => btn.classList.remove('copied'), 2000);
}

async function regenerateResponse(messageDiv) {
  // Find the previous user message
  const messages = elements.messagesContainer.querySelectorAll('.message');
  let userMessage = null;

  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i] === messageDiv && i > 0) {
      // Look for user message before this
      for (let j = i - 1; j >= 0; j--) {
        if (messages[j].dataset.role === 'user') {
          userMessage = messages[j].querySelector('.message-text').textContent;
          break;
        }
      }
      break;
    }
  }

  if (!userMessage) return;

  // Remove the old assistant message
  messageDiv.remove();

  // Send the message again
  await handleNewMessage(userMessage);
}

function editMessage(messageDiv) {
  const textElement = messageDiv.querySelector('.message-text');
  const currentText = textElement.textContent.trim();

  // Create edit form
  const editForm = document.createElement('div');
  editForm.className = 'edit-form';
  editForm.innerHTML = `
    <textarea class="edit-textarea">${escapeHtml(currentText)}</textarea>
    <div class="edit-actions">
      <button type="button" class="edit-save-btn">Save & Submit</button>
      <button type="button" class="edit-cancel-btn">Cancel</button>
    </div>
  `;

  // Hide the text and show edit form
  textElement.style.display = 'none';
  messageDiv.querySelector('.message-body').insertBefore(editForm, textElement.nextSibling);

  const textarea = editForm.querySelector('.edit-textarea');
  textarea.focus();
  textarea.setSelectionRange(textarea.value.length, textarea.value.length);

  // Auto-resize
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';

  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
  });

  // Cancel button
  editForm.querySelector('.edit-cancel-btn').addEventListener('click', () => {
    editForm.remove();
    textElement.style.display = '';
  });

  // Save button
  editForm.querySelector('.edit-save-btn').addEventListener('click', async () => {
    const newText = textarea.value.trim();
    if (!newText) return;

    // Find this message's index and remove all messages after it
    const messages = elements.messagesContainer.querySelectorAll('.message');
    let foundIndex = -1;

    for (let i = 0; i < messages.length; i++) {
      if (messages[i] === messageDiv) {
        foundIndex = i;
        break;
      }
    }

    if (foundIndex >= 0) {
      // Remove all messages from this one onwards
      for (let i = messages.length - 1; i >= foundIndex; i--) {
        messages[i].remove();
      }
    }

    // Add the edited message and get new response
    addMessage('user', newText);
    await handleNewMessage(newText);
  });
}

function updateSendButton() {
  const hasText = elements.messageInput.value.trim().length > 0;
  elements.sendBtn.disabled = !hasText || state.isLoading;

  // Toggle stop button visibility
  if (elements.stopBtn) {
    elements.stopBtn.style.display = state.isLoading ? 'flex' : 'none';
    elements.sendBtn.style.display = state.isLoading ? 'none' : 'flex';
  }
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

    item.addEventListener('click', (e) => {
      if (!e.target.closest('.conversation-delete')) {
        loadConversation(conv.id);
      }
    });

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

  elements.messagesContainer.innerHTML = '';
  hideWelcome();

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

async function handleNewMessage(message) {
  hideWelcome();

  const assistantMessage = addMessage('assistant', '', true);

  state.isLoading = true;
  state.abortController = new AbortController();
  updateSendButton();

  try {
    await sendMessageStream(
      message,
      state.currentConversationId,
      (content) => {
        // Update message with streamed content
        updateMessage(assistantMessage, content);
      },
      (conversationId) => {
        // On done
        if (!state.currentConversationId) {
          state.currentConversationId = conversationId;
        }
        refreshConversations();
      },
      state.abortController.signal
    );
  } catch (error) {
    if (error.name === 'AbortError') {
      // User stopped generation
      const textElement = assistantMessage.querySelector('.message-text');
      if (textElement.querySelector('.typing-indicator')) {
        textElement.innerHTML = '<em>Generation stopped</em>';
      }
    } else {
      updateMessage(assistantMessage, `**Error:** ${error.message}`);
    }
  } finally {
    state.isLoading = false;
    state.abortController = null;
    updateSendButton();
  }
}

async function handleSubmit(e) {
  e.preventDefault();

  const message = elements.messageInput.value.trim();
  if (!message || state.isLoading) return;

  elements.messageInput.value = '';
  autoResizeTextarea();
  updateSendButton();

  addMessage('user', message);
  await handleNewMessage(message);
}

function stopGeneration() {
  if (state.abortController) {
    state.abortController.abort();
  }
}

// ========== SIDEBAR MOBILE ==========

function toggleSidebar() {
  elements.sidebar.classList.toggle('open');
}

function closeSidebar() {
  elements.sidebar.classList.remove('open');
}

// ========== KEYBOARD SHORTCUTS ==========

function handleGlobalKeydown(e) {
  // Ctrl/Cmd + N = New chat
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault();
    startNewChat();
  }

  // Escape = Stop generation
  if (e.key === 'Escape' && state.isLoading) {
    stopGeneration();
  }

  // Ctrl/Cmd + Shift + C = Copy last response
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C') {
    e.preventDefault();
    const lastAssistant = elements.messagesContainer.querySelector('.message.assistant:last-of-type');
    if (lastAssistant) {
      copyMessageContent(lastAssistant);
    }
  }
}

// ========== EXPORT CHAT ==========

function exportChat() {
  const messages = elements.messagesContainer.querySelectorAll('.message');
  let markdown = `# Veritas Chat Export\n\nExported: ${new Date().toLocaleString()}\n\n---\n\n`;

  messages.forEach(msg => {
    const role = msg.dataset.role === 'user' ? '**You**' : '**Veritas**';
    const text = msg.querySelector('.message-text').textContent.trim();
    markdown += `${role}:\n\n${text}\n\n---\n\n`;
  });

  const blob = new Blob([markdown], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `veritas-chat-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// Make exportChat available globally
window.exportChat = exportChat;

// ========== UTILS ==========

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ========== EVENT LISTENERS ==========

elements.chatForm.addEventListener('submit', handleSubmit);

elements.messageInput.addEventListener('input', () => {
  updateSendButton();
  autoResizeTextarea();
});

elements.messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    elements.chatForm.dispatchEvent(new Event('submit'));
  }
});

elements.newChatBtn.addEventListener('click', () => {
  startNewChat();
  closeSidebar();
});

elements.clearAllBtn.addEventListener('click', async () => {
  if (confirm('Are you sure you want to delete all conversations?')) {
    await clearAllConversations();
    await refreshConversations();
    startNewChat();
  }
});

elements.sidebarToggle.addEventListener('click', toggleSidebar);

if (elements.themeToggle) {
  elements.themeToggle.addEventListener('click', toggleTheme);
}

if (elements.stopBtn) {
  elements.stopBtn.addEventListener('click', stopGeneration);
}

document.querySelectorAll('.suggestion-card').forEach(card => {
  card.addEventListener('click', () => {
    const prompt = card.dataset.prompt;
    elements.messageInput.value = prompt;
    autoResizeTextarea();
    updateSendButton();
    elements.messageInput.focus();
  });
});

document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768) {
    if (!elements.sidebar.contains(e.target) && !elements.sidebarToggle.contains(e.target)) {
      closeSidebar();
    }
  }
});

document.addEventListener('keydown', handleGlobalKeydown);

// ========== INIT ==========

async function init() {
  initTheme();
  await refreshConversations();
  elements.messageInput.focus();
}

init();
