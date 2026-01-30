# Browser Extension Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Chrome Extension (Manifest V3) for quick content capture and web page annotation, syncing to the knowledge base backend.

**Architecture:** Chrome Extension with Background Service Worker, Content Scripts, and Popup. Communicates with existing Flask backend via REST API. Real-time sync with offline queue support.

**Tech Stack:** Chrome Extension Manifest V3, Vanilla JavaScript, Chrome Storage API, Flask backend, SQLite database.

---

## Task 1: Backend API - Plugin Submit Endpoint

**Files:**
- Modify: `backend/models.py` (add card_annotations table)
- Modify: `backend/routes/knowledge_base.py` (add API endpoints)
- Test: `tests/test_routes.py`

**Step 1: Create database migration for annotations table**

Add to `backend/models.py` after the cards table definition:

```python
def init_card_annotations_table():
    """初始化卡片标注表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            card_id INTEGER,
            source_url TEXT NOT NULL,
            annotation_text TEXT,
            xpath TEXT,
            color TEXT DEFAULT 'yellow',
            note TEXT,
            annotation_type TEXT DEFAULT 'highlight',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (card_id) REFERENCES cards(id)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_annotations_user_url
        ON card_annotations(user_id, source_url)
    ''')

    conn.commit()
    conn.close()

    print("Card annotations table initialized")
```

**Step 2: Run migration to create table**

Run: `python3 -c "from backend.models import init_card_annotations_table; init_card_annotations_table()"`

Expected: "Card annotations table initialized"

**Step 3: Write failing test for plugin submit endpoint**

Add to `tests/test_routes.py`:

```python
    def test_plugin_submit_content(self, client, test_admin_user):
        """测试插件提交内容"""
        from models import create_user, generate_api_key

        # Create user with API key
        password_hash = generate_password_hash('TestPass123!')
        user_id = create_user('extuser', password_hash, role='author')
        api_key = generate_api_key(user_id)

        # Submit via plugin API
        response = client.post('/api/plugin/submit',
            json={
                'title': 'Test Page',
                'content': 'Selected text from page',
                'source_url': 'https://example.com/test',
                'tags': ['test', 'plugin']
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'card_id' in data
```

**Step 4: Run test to verify it fails**

Run: `pytest tests/test_routes.py::TestKnowledgeBaseRoutes::test_plugin_submit_content -v`

Expected: 404 (endpoint doesn't exist)

**Step 5: Implement API key helper functions**

Add to `backend/models.py`:

```python
def generate_api_key(user_id):
    """生成API密钥"""
    import secrets
    api_key = secrets.token_urlsafe(32)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO api_keys (user_id, api_key, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, api_key))

    conn.commit()
    conn.close()

    return api_key

def validate_api_key(api_key):
    """验证API密钥并返回user_id"""
    if not api_key:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id FROM api_keys
        WHERE api_key = ? AND is_active = 1
    ''', (api_key,))

    result = cursor.fetchone()
    conn.close()

    return result['user_id'] if result else None
```

Also add api_keys table creation:

```python
def init_api_keys_table():
    """初始化API密钥表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
```

**Step 6: Implement plugin submit endpoint**

Add to `backend/routes/knowledge_base.py`:

```python
def api_key_required(f):
    """API密钥认证装饰器"""
    from functools import wraps
    from models import validate_api_key

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        user_id = validate_api_key(api_key)

        if not user_id:
            return jsonify({'success': False, 'error': 'Invalid or missing API key'}), 401

        # Store user_id in flask.g for use in the route
        g.user_id = user_id
        return f(*args, **kwargs)

    return decorated_function


@knowledge_base_bp.route('/api/plugin/submit', methods=['POST'])
@api_key_required
def plugin_submit():
    """接收浏览器插件提交的内容"""
    from models import create_card

    data = request.get_json()
    title = data.get('title', 'Untitled')
    content = data.get('content', '')
    source_url = data.get('source_url', '')
    tags = data.get('tags', [])
    annotation_type = data.get('annotation_type', 'capture')

    if not content:
        return jsonify({'success': False, 'error': 'Content is required'}), 400

    # Build full content with metadata
    full_content = f"Source: {source_url}\n\n{content}"

    # Create card
    card_id = create_card(
        user_id=g.user_id,
        title=title,
        content=full_content,
        status='idea',
        source='browser-extension',
        tags=tags
    )

    log_operation(g.user_id, 'Plugin',
                 f'Plugin submitted content', f'Source: {source_url}')

    return jsonify({
        'success': True,
        'card_id': card_id,
        'message': 'Saved successfully'
    })
```

**Step 7: Run test to verify it passes**

Run: `pytest tests/test_routes.py::TestKnowledgeBaseRoutes::test_plugin_submit_content -v`

Expected: PASS

**Step 8: Commit**

```bash
git add backend/models.py backend/routes/knowledge_base.py tests/test_routes.py
git commit -m "feat: add plugin submit API endpoint"
```

---

## Task 2: Backend API - Annotation Sync Endpoints

**Files:**
- Modify: `backend/models.py` (annotation CRUD functions)
- Modify: `backend/routes/knowledge_base.py` (annotation sync endpoints)
- Test: `tests/test_routes.py`

**Step 1: Write failing test for annotation sync**

Add to `tests/test_routes.py`:

```python
    def test_plugin_sync_annotations(self, client, test_admin_user):
        """测试插件同步标注"""
        from models import create_user, generate_api_key

        user_id = create_user('extuser2', generate_password_hash('TestPass123!'), role='author')
        api_key = generate_api_key(user_id)

        response = client.post('/api/plugin/sync-annotations',
            json={
                'url': 'https://example.com/test',
                'annotations': [
                    {
                        'id': 'uuid-1',
                        'text': 'Selected text',
                        'xpath': '/html/body/p[1]',
                        'color': 'yellow',
                        'note': 'My note',
                        'annotation_type': 'highlight'
                    }
                ]
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        assert data['success'] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_routes.py::TestKnowledgeBaseRoutes::test_plugin_sync_annotations -v`

Expected: 404 (endpoint doesn't exist)

**Step 3: Implement annotation model functions**

Add to `backend/models.py`:

```python
def create_annotation(user_id, source_url, annotation_text, xpath, color, note, annotation_type='highlight', card_id=None):
    """创建标注"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO card_annotations
        (user_id, card_id, source_url, annotation_text, xpath, color, note, annotation_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, card_id, source_url, annotation_text, xpath, color, note, annotation_type))

    annotation_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return annotation_id

def get_annotations_by_url(user_id, source_url):
    """获取指定URL的所有标注"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM card_annotations
        WHERE user_id = ? AND source_url = ?
        ORDER BY created_at DESC
    ''', (user_id, source_url))

    annotations = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return annotations
```

**Step 4: Implement annotation sync endpoints**

Add to `backend/routes/knowledge_base.py`:

```python
@knowledge_base_bp.route('/api/plugin/sync-annotations', methods=['POST'])
@api_key_required
def sync_annotations():
    """同步页面标注数据"""
    from models import create_annotation

    data = request.get_json()
    url = data.get('url')
    annotations = data.get('annotations', [])

    if not url or not annotations:
        return jsonify({'success': False, 'error': 'URL and annotations required'}), 400

    try:
        annotation_ids = []
        for ann in annotations:
            ann_id = create_annotation(
                user_id=g.user_id,
                source_url=url,
                annotation_text=ann.get('text'),
                xpath=ann.get('xpath'),
                color=ann.get('color', 'yellow'),
                note=ann.get('note'),
                annotation_type=ann.get('annotation_type', 'highlight')
            )
            annotation_ids.append(ann_id)

        return jsonify({
            'success': True,
            'annotation_ids': annotation_ids,
            'count': len(annotation_ids)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/api/plugin/annotations', methods=['GET'])
@api_key_required
def get_annotations():
    """获取指定URL的所有标注"""
    from models import get_annotations_by_url

    url = request.args.get('url')

    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400

    try:
        annotations = get_annotations_by_url(g.user_id, url)

        return jsonify({
            'success': True,
            'annotations': annotations,
            'count': len(annotations)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_routes.py::TestKnowledgeBaseRoutes::test_plugin_sync_annotations -v`

Expected: PASS

**Step 6: Commit**

```bash
git add backend/models.py backend/routes/knowledge_base.py tests/test_routes.py
git commit -m "feat: add annotation sync API endpoints"
```

---

## Task 3: Browser Extension - Project Setup

**Files:**
- Create: `browser-extension/manifest.json`
- Create: `browser-extension/background/service-worker.js`
- Create: `browser-extension/background/api-client.js`
- Create: `browser-extension/background/auth-manager.js`
- Create: `browser-extension/icons/icon16.png` (placeholder)
- Create: `browser-extension/icons/icon48.png` (placeholder)
- Create: `browser-extension/icons/icon128.png` (placeholder)

**Step 1: Create browser extension directory structure**

Run: `mkdir -p browser-extension/{background,content,popup,icons,tests}`

**Step 2: Create manifest.json**

Create `browser-extension/manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "知识库快速捕获",
  "version": "1.0.0",
  "description": "快速保存网页内容到个人知识库",

  "permissions": [
    "activeTab",
    "storage",
    "scripting"
  ],

  "host_permissions": [
    "http://localhost:5001/*"
  ],

  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },

  "background": {
    "service_worker": "background/service-worker.js"
  },

  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content/content.js"],
      "css": ["content/content.css"],
      "run_at": "document_end"
    }
  ],

  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

**Step 3: Create service worker**

Create `browser-extension/background/service-worker.js`:

```javascript
// Service Worker for browser extension

console.log('Knowledge Base Extension Service Worker loaded');

// Install event
self.addEventListener('install', (event) => {
  console.log('Extension installed');
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('Extension activated');
  event.waitUntil(self.clients.claim());
});

// Handle messages from content scripts and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Received message:', request);

  if (request.action === 'submitContent') {
    // Forward to API client
    import('./api-client.js').then(module => {
      module.submitContent(request.data)
        .then(response => sendResponse({success: true, data: response}))
        .catch(error => sendResponse({success: false, error: error.message}));
    });
    return true; // Keep message channel open for async response
  }

  if (request.action === 'getAnnotations') {
    import('./api-client.js').then(module => {
      module.getAnnotations(request.url)
        .then(annotations => sendResponse({success: true, annotations}))
        .catch(error => sendResponse({success: false, error: error.message}));
    });
    return true;
  }
});
```

**Step 4: Create API client**

Create `browser-extension/background/api-client.js`:

```javascript
// API client for communicating with backend

const API_BASE = 'http://localhost:5001';

// Get API key from storage
async function getAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => {
      resolve(result.apiKey);
    });
  });
}

// Submit content to backend
export async function submitContent(data) {
  const apiKey = await getAPIKey();

  if (!apiKey) {
    throw new Error('API key not configured. Please set your API key in extension settings.');
  }

  const response = await fetch(`${API_BASE}/api/plugin/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Sync annotations to backend
export async function syncAnnotations(url, annotations) {
  const apiKey = await getAPIKey();

  if (!apiKey) {
    throw new Error('API key not configured');
  }

  const response = await fetch(`${API_BASE}/api/plugin/sync-annotations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    },
    body: JSON.stringify({ url, annotations })
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Get annotations from backend
export async function getAnnotations(url) {
  const apiKey = await getAPIKey();

  if (!apiKey) {
    throw new Error('API key not configured');
  }

  const response = await fetch(`${API_BASE}/api/plugin/annotations?url=${encodeURIComponent(url)}`, {
    method: 'GET',
    headers: {
      'X-API-Key': apiKey
    }
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
```

**Step 5: Create auth manager**

Create `browser-extension/background/auth-manager.js`:

```javascript
// Authentication manager for API key

// Save API key
export async function setAPIKey(apiKey) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ apiKey }, () => {
      console.log('API key saved');
      resolve(true);
    });
  });
}

// Get API key
export async function getAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => {
      resolve(result.apiKey || null);
    });
  });
}

// Clear API key
export async function clearAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.remove(['apiKey'], () => {
      console.log('API key cleared');
      resolve(true);
    });
  });
}

// Validate API key with backend
export async function validateAPIKey(apiKey) {
  const API_BASE = 'http://localhost:5001';

  try {
    const response = await fetch(`${API_BASE}/api/plugin/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      }
    });

    return response.ok;
  } catch (error) {
    console.error('Validation error:', error);
    return false;
  }
}
```

**Step 6: Create placeholder icons**

Run:
```bash
cd browser-extension/icons
# Create simple SVG icons converted to PNG
# For now, create placeholder files
echo "Placeholder" > icon16.png
echo "Placeholder" > icon48.png
echo "Placeholder" > icon128.png
```

**Step 7: Commit**

```bash
git add browser-extension/
git commit -m "feat: set up browser extension project structure"
```

---

## Task 4: Content Script - Text Selection & Toolbar

**Files:**
- Create: `browser-extension/content/content.js`
- Create: `browser-extension/content/content.css`
- Create: `browser-extension/content/selector.js`
- Create: `browser-extension/content/toolbar.js`

**Step 1: Create content script main file**

Create `browser-extension/content/content.js`:

```javascript
// Content script for web page interaction

console.log('Knowledge Base Content Script loaded');

import Selector from './selector.js';
import Toolbar from './toolbar.js';

// Initialize components
const selector = new Selector();
const toolbar = new Toolbar();

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSelectedContent') {
    const selection = selector.getSelection();
    sendResponse({ success: true, data: selection });
  }
  return true;
});
```

**Step 2: Create selector module**

Create `browser-extension/content/selector.js`:

```javascript
// Text selection handler

export default class Selector {
  constructor() {
    this.init();
  }

  init() {
    // Listen for text selection
    document.addEventListener('mouseup', () => this.handleSelection());
    document.addEventListener('touchend', () => this.handleSelection());
  }

  handleSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText.length > 0) {
      console.log('Text selected:', selectedText);
      // Notify toolbar to show
      this.showToolbar(selection);
    } else {
      this.hideToolbar();
    }
  }

  showToolbar(selection) {
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    // Send event to toolbar
    const event = new CustomEvent('kb:showToolbar', {
      detail: {
        text: selection.toString(),
        rect: rect,
        x: rect.left + rect.width / 2,
        y: rect.top - 50
      }
    });

    document.dispatchEvent(event);
  }

  hideToolbar() {
    const event = new CustomEvent('kb:hideToolbar');
    document.dispatchEvent(event);
  }

  getSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (!selectedText) {
      return null;
    }

    return {
      text: selectedText,
      html: selection.getRangeAt(0).cloneContents(),
      url: window.location.href,
      title: document.title
    };
  }

  clearSelection() {
    window.getSelection().removeAllRanges();
  }
}
```

**Step 3: Create toolbar module**

Create `browser-extension/content/toolbar.js`:

```javascript
// Floating toolbar for quick actions

export default class Toolbar {
  constructor() {
    this.toolbar = null;
    this.init();
  }

  init() {
    // Create toolbar element
    this.createToolbar();

    // Listen for show/hide events
    document.addEventListener('kb:showToolbar', (e) => this.show(e.detail));
    document.addEventListener('kb:hideToolbar', () => this.hide());
  }

  createToolbar() {
    this.toolbar = document.createElement('div');
    this.toolbar.className = 'kb-toolbar';
    this.toolbar.innerHTML = `
      <button class="kb-btn kb-btn-save" title="保存">📌</button>
      <button class="kb-btn kb-btn-tag" title="保存并添加标签">🏷️</button>
      <button class="kb-btn kb-btn-note" title="保存并添加备注">✏️</button>
      <button class="kb-btn kb-btn-close" title="关闭">❌</button>
    `;

    // Attach event listeners
    this.toolbar.querySelector('.kb-btn-save').addEventListener('click', () => this.saveSelection());
    this.toolbar.querySelector('.kb-btn-tag').addEventListener('click', () => this.saveWithTags());
    this.toolbar.querySelector('.kb-btn-note').addEventListener('click', () => this.saveWithNote());
    this.toolbar.querySelector('.kb-btn-close').addEventListener('click', () => this.hide());

    document.body.appendChild(this.toolbar);
  }

  show(detail) {
    this.currentSelection = detail;

    // Position toolbar
    this.toolbar.style.left = `${detail.x}px`;
    this.toolbar.style.top = `${detail.y}px`;
    this.toolbar.style.display = 'block';
  }

  hide() {
    this.toolbar.style.display = 'none';
    this.currentSelection = null;
  }

  async saveSelection() {
    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: [],
      annotation_type: 'capture'
    };

    await this.submitToBackend(content);
    this.hide();
  }

  async saveWithTags() {
    const tags = prompt('Enter tags (comma separated):');
    if (!tags) return;

    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: tags.split(',').map(t => t.trim()),
      annotation_type: 'capture'
    };

    await this.submitToBackend(content);
    this.hide();
  }

  async saveWithNote() {
    const note = prompt('Add a note:');
    if (!note) return;

    const content = {
      title: document.title,
      content: `${this.currentSelection.text}\n\nNote: ${note}`,
      source_url: window.location.href,
      tags: ['note'],
      annotation_type: 'note'
    };

    await this.submitToBackend(content);
    this.hide();
  }

  async submitToBackend(content) {
    try {
      // Send message to background script
      const response = await chrome.runtime.sendMessage({
        action: 'submitContent',
        data: content
      });

      if (response.success) {
        this.showNotification('✅ Saved to knowledge base!');
        console.log('Saved:', response.data);
      } else {
        this.showNotification('❌ Failed to save');
        console.error('Error:', response.error);
      }
    } catch (error) {
      this.showNotification('❌ Error: ' + error.message);
      console.error('Error:', error);
    }
  }

  showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'kb-notification';
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #333;
      color: white;
      padding: 12px 20px;
      border-radius: 4px;
      z-index: 10000;
      animation: kb-slide-in 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}
```

**Step 4: Create content script styles**

Create `browser-extension/content/content.css`:

```css
/* Knowledge Base Extension Styles */

.kb-toolbar {
  position: absolute;
  display: none;
  background: white;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 9999;
  transform: translateX(-50%);
}

.kb-toolbar::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 8px 8px 0;
  border-style: solid;
  border-color: white transparent transparent transparent;
}

.kb-btn {
  background: none;
  border: none;
  font-size: 20px;
  padding: 6px 10px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.kb-btn:hover {
  background: #f0f0f0;
}

.kb-notification {
  animation: kb-slide-in 0.3s ease-out;
}

@keyframes kb-slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
```

**Step 5: Commit**

```bash
git add browser-extension/content/
git commit -m "feat: add content script with text selection and toolbar"
```

---

## Task 5: Popup Interface

**Files:**
- Create: `browser-extension/popup/popup.html`
- Create: `browser-extension/popup/popup.js`
- Create: `browser-extension/popup/popup.css`

**Step 1: Create popup HTML**

Create `browser-extension/popup/popup.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>知识库</title>
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <div class="popup-container">
    <header class="popup-header">
      <div class="user-info">
        <span class="status-indicator" id="syncStatus"></span>
        <span class="user-name">知识库</span>
      </div>
    </header>

    <main class="popup-main">
      <div class="recent-captures" id="recentCaptures">
        <p class="empty-state">No recent captures</p>
      </div>
    </main>

    <footer class="popup-footer">
      <button id="quickNoteBtn" class="btn btn-primary">
        📝 Quick Note
      </button>
      <a href="http://localhost:5001/timeline" target="_blank" class="btn btn-secondary">
        📚 Open Knowledge Base
      </a>
      <button id="settingsBtn" class="btn btn-icon">
        ⚙️
      </button>
    </footer>
  </div>

  <script type="module" src="popup.js"></script>
</body>
</html>
```

**Step 2: Create popup JavaScript**

Create `browser-extension/popup/popup.js`:

```javascript
// Popup controller

console.log('Popup loaded');

document.addEventListener('DOMContentLoaded', () => {
  init();
});

function init() {
  loadRecentCaptures();
  setupEventListeners();
  checkAPIKeyStatus();
}

function setupEventListeners() {
  document.getElementById('quickNoteBtn').addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:5001/quick-note' });
  });

  document.getElementById('settingsBtn').addEventListener('click', () => {
    showSettingsDialog();
  });
}

async function loadRecentCaptures() {
  // This would fetch from backend or local storage
  // For now, show placeholder
  const container = document.getElementById('recentCaptures');

  // Try to get from local storage
  chrome.storage.local.get(['recentCaptures'], (result) => {
    const captures = result.recentCaptures || [];

    if (captures.length === 0) {
      container.innerHTML = '<p class="empty-state">No recent captures</p>';
      return;
    }

    container.innerHTML = captures.map(capture => `
      <div class="capture-item" data-id="${capture.id}">
        <h4>${escapeHtml(capture.title)}</h4>
        <p class="preview">${escapeHtml(capture.content.substring(0, 100))}...</p>
        <span class="time">${formatTime(capture.created_at)}</span>
      </div>
    `).join('');
  });
}

function checkAPIKeyStatus() {
  const statusEl = document.getElementById('syncStatus');

  chrome.storage.local.get(['apiKey'], (result) => {
    if (result.apiKey) {
      statusEl.className = 'status-indicator status-ok';
      statusEl.title = 'Connected';
    } else {
      statusEl.className = 'status-indicator status-error';
      statusEl.title = 'Not configured - click settings to setup';
    }
  });
}

function showSettingsDialog() {
  const apiKey = prompt('Enter your API Key (from Knowledge Base settings):');

  if (apiKey) {
    chrome.storage.local.set({ apiKey }, () => {
      alert('API Key saved!');
      checkAPIKeyStatus();
    });
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}
```

**Step 3: Create popup styles**

Create `browser-extension/popup/popup.css`:

```css
/* Popup styles */

body {
  width: 350px;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
}

.popup-container {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.popup-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #f5f5f5;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-ok {
  background: #4caf50;
}

.status-error {
  background: #f44336;
}

.popup-main {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.recent-captures {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.capture-item {
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.capture-item:hover {
  border-color: #2196f3;
}

.capture-item h4 {
  margin: 0 0 6px 0;
  font-size: 14px;
  font-weight: 600;
}

.capture-item .preview {
  margin: 0 0 8px 0;
  color: #666;
  font-size: 13px;
  line-height: 1.4;
}

.capture-item .time {
  font-size: 12px;
  color: #999;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 40px 20px;
}

.popup-footer {
  padding: 12px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-primary:hover {
  background: #1976d2;
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

.btn-icon {
  width: 36px;
  padding: 0;
  background: none;
  font-size: 18px;
}
```

**Step 4: Commit**

```bash
git add browser-extension/popup/
git commit -m "feat: add popup interface"
```

---

## Task 6: Testing & Documentation

**Files:**
- Create: `browser-extension/README.md`
- Create: `browser-extension/tests/README.md`

**Step 1: Create README**

Create `browser-extension/README.md`:

```markdown
# Knowledge Base Browser Extension

Chrome Extension for quick content capture and web page annotation.

## Installation

### Development Mode

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `browser-extension` directory
5. Extension should now appear in your toolbar

### Configuration

1. Click the extension icon in toolbar
2. Click settings (gear icon)
3. Enter your API Key from Knowledge Base settings
4. You're ready to capture!

## Features

- **Quick Capture**: Select text on any webpage, click save button
- **Add Tags**: Save with custom tags for organization
- **Add Notes**: Attach notes to captured content
- **Auto Metadata**: Page title and URL automatically saved

## Usage

1. Navigate to any webpage
2. Select text with your mouse
3. Click the 📌 button in the floating toolbar
4. Content is saved to your knowledge base!

## Development

### File Structure

- `manifest.json` - Extension configuration
- `background/` - Service worker and API communication
- `content/` - Scripts injected into web pages
- `popup/` - Extension popup interface
- `icons/` - Extension icons

### Testing

1. Load extension in dev mode
2. Navigate to a webpage
3. Select text and verify toolbar appears
4. Click save and check knowledge base

## Troubleshooting

**Toolbar not appearing?**
- Ensure you've selected text (highlight with mouse)
- Check browser console for errors

**Save failing?**
- Verify API key is configured
- Check backend is running at localhost:5001
- Open browser DevTools Console for error messages

## License

MIT
```

**Step 2: Commit**

```bash
git add browser-extension/
git commit -m "docs: add browser extension README"
```

**Step 3: Run full test suite**

Run: `pytest tests/ -v`

Expected: All tests pass (including new plugin API tests)

**Step 4: Final commit**

```bash
git add .
git commit -m "feat: browser extension implementation complete

- Plugin submit API endpoint
- Annotation sync endpoints
- Content script with text selection
- Floating toolbar with save actions
- Popup interface
- Complete documentation"
```

---

## Completion Checklist

- [x] Backend API endpoints for plugin content submit
- [x] Backend API endpoints for annotation sync
- [x] Database tables for annotations and API keys
- [x] Browser extension manifest and structure
- [x] Content script with text selection
- [x] Floating toolbar UI
- [x] Background service worker
- [x] API client for backend communication
- [x] Popup interface
- [x] Documentation
- [x] All tests passing

**Phase 3 Complete!** 🎉

The browser extension is ready for:
1. Manual testing in Chrome
2. Icon design and creation
3. Chrome Web Store submission (future)
4. Firefox port (future)
