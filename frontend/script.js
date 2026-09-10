// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton, themeToggle;

// Theme management
const THEME_STORAGE_KEY = 'course-rag-theme';
const LIGHT_THEME = 'light';
const DARK_THEME = 'dark';

// Initialize theme on page load before DOM renders
function initializeTheme() {
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? DARK_THEME : LIGHT_THEME);
    applyTheme(theme);
}

function applyTheme(theme) {
    if (theme === LIGHT_THEME) {
        document.documentElement.classList.add('light-theme');
    } else {
        document.documentElement.classList.remove('light-theme');
    }
    localStorage.setItem(THEME_STORAGE_KEY, theme);
}

function toggleTheme() {
    const isDarkMode = document.documentElement.classList.contains('light-theme');
    const newTheme = isDarkMode ? DARK_THEME : LIGHT_THEME;
    applyTheme(newTheme);
}

// Apply theme before rendering
initializeTheme();

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // New chat
    newChatButton.addEventListener('click', startNewChat);

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${renderSources(sources)}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Render the Sources section: dedupe, group by course, show lessons as pill links
function renderSources(sources) {
    const seen = new Set();
    const groups = new Map();

    for (const source of sources) {
        // Tolerate the old plain-string shape as well as {text, link}
        const { text, link } = typeof source === 'string'
            ? { text: source, link: null }
            : source;
        if (!text) continue;

        const dedupeKey = `${text}|${link || ''}`;
        if (seen.has(dedupeKey)) continue;
        seen.add(dedupeKey);

        const match = text.match(/^(.*?)\s*-\s*Lesson\s+(\d+)$/i);
        const course = match ? match[1] : text;
        const label = match ? `Lesson ${match[2]}` : text;

        if (!groups.has(course)) groups.set(course, []);
        groups.get(course).push({ label, link });
    }

    return Array.from(groups.entries()).map(([course, entries]) => {
        const pills = entries.map(({ label, link }) => {
            const safeLabel = escapeHtml(label);
            return link
                ? `<a class="source-pill" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${safeLabel}</a>`
                : `<span class="source-pill">${safeLabel}</span>`;
        }).join('');
        return `<div class="source-group">
                    <div class="source-course">${escapeHtml(course)}</div>
                    <div class="source-pills">${pills}</div>
                </div>`;
    }).join('');
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistantttt! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Tear down the current session (frontend + backend) and start a fresh one in place
async function startNewChat() {
    const oldSessionId = currentSessionId;
    if (oldSessionId) {
        try {
            await fetch(`${API_URL}/session/${oldSessionId}`, { method: 'DELETE' });
        } catch (error) {
            console.error('Failed to clear session on server:', error);
        }
    }
    createNewSession();
    chatInput.value = '';
    chatInput.focus();
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}