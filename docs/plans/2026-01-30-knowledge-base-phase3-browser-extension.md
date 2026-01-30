# Knowledge Base Phase 3 - Browser Extension Design

**Date:** 2026-01-30
**Status:** Design Approved
**Implementation:** Ready to Start

---

## Overview

Phase 3 implements a **Chrome Extension** for quick content capture and web page annotation, enabling users to seamlessly save web content to their knowledge base.

**Core Features:**
- Quick content capture (text + metadata)
- Web page annotation and notes
- Real-time sync to server
- Offline queue support
- Chrome Extension Manifest V3

**Estimated Timeline:** 4 weeks

---

## Part 1: System Architecture

### Overall Architecture

The browser extension uses **Chrome Extension Manifest V3** architecture with three core components:

**Popup (弹出窗口)**
- Displayed when user clicks toolbar icon
- Quick access to recent captures
- One-click navigation to knowledge base
- Sync status and login state indicators

**Content Script (内容脚本)**
- Injected into web pages user browses
- Implements text selection and image capture
- Provides floating toolbar for quick annotation
- Communicates with Background via Chrome Runtime API

**Background Service Worker**
- Background service for extension
- Handles API requests and authentication
- Manages offline queue and synchronization
- Monitors browser tab lifecycle

### Data Flow

```
User selects text/image → Content Script captures
                    ↓
            Background Service Worker
                    ↓
              Knowledge Base API (POST /api/plugin/submit)
                    ↓
              Server saves to cards table
                    ↓
            Return card ID with confirmation
```

---

## Part 2: Core Features

### 2.1 Quick Content Capture

**Text Capture**
- Auto-show floating toolbar when user selects text on webpage
- Toolbar options:
  - 📌 Save selected content
  - 🏷️ Save and add tags
  - ✏️ Save and add note
  - ❌ Close

**Metadata Auto-Extraction**
- Page title (as card title)
- Page URL (saved to card content)
- Selected text (saved as card content)
- Page favicon (for display)
- Capture timestamp

**Smart Classification**
- Auto-infer source from page URL
- Mark `source='browser-extension'`
- Configurable default tag rules in settings

### 2.2 Web Page Annotation & Notes

**Annotation Features**
- Highlight text (yellow/green/blue/red)
- Add text notes (displayed as sidebar sticky notes)
- Underline/strikethrough
- All annotations persisted locally

**Annotation Storage**
- Use URL as key to store annotation data
- Each annotation contains: selected text, position, color, note
- Sync to server extension table via API

**Revisiting Pages**
- Auto-load and display previous annotations
- Support edit/delete existing annotations
- Annotation view toggle (show/hide)

### 2.3 Popup Interface

**Layout**
- Top: User avatar + sync status
- Middle: Recent 5 captures list
  - Display title, preview, time
  - Click to jump to knowledge base edit
- Bottom:
  - "Quick Note" button
  - "Go to Knowledge Base" link
  - Settings entry

---

## Part 3: API Design & Data Model

### 3.1 Backend API Endpoints

**Plugin Content Submit API**
```python
@knowledge_base_bp.route('/api/plugin/submit', methods=['POST'])
@api_key_required  # Use extension API key authentication
def plugin_submit():
    """
    Receive content submitted from browser extension

    Request:
    {
        "title": "Page Title",
        "content": "Selected text content",
        "source_url": "https://example.com",
        "tags": ["tag1", "tag2"],
        "annotation_type": "highlight",  # highlight/note/both
        "annotation_data": {...},  # Annotation details
        "screenshot": "base64..."  # optional
    }

    Response:
    {
        "success": true,
        "card_id": 123,
        "message": "Saved successfully"
    }
    """
```

**Annotation Sync API**
```python
@knowledge_base_bp.route('/api/plugin/sync-annotations', methods=['POST'])
@api_key_required
def sync_annotations():
    """
    Sync page annotation data

    Request:
    {
        "url": "https://example.com",
        "annotations": [
            {
                "id": "uuid",
                "text": "Selected text",
                "xpath": "/html/body/div[1]/p[2]",
                "color": "yellow",
                "note": "User note",
                "created_at": "2026-01-30T10:00:00Z"
            }
        ]
    }
    """
```

**Get Page Annotations API**
```python
@knowledge_base_bp.route('/api/plugin/annotations', methods=['GET'])
@api_key_required
def get_annotations():
    """
    Get all annotations for specified URL
    ?url=https://example.com
    """
```

### 3.2 Database Extension

**New Table: `card_annotations`**
```sql
CREATE TABLE card_annotations (
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
);

CREATE INDEX idx_annotations_user_url ON card_annotations(user_id, source_url);
```

---

## Part 4: Extension Configuration & Security

### 4.1 Manifest V3 Configuration

**manifest.json Structure**
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
    "https://yourdomain.com/*"
  ],

  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },

  "background": {
    "service_worker": "background.js"
  },

  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "css": ["content.css"],
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

### 4.2 Authentication & Security

**API Key Mechanism**
- User generates extension API key in knowledge base settings
- Key stored in `chrome.storage.local`
- Send with each API request in Header: `X-API-Key: xxxxx`
- Server validates key validity

**CORS Configuration**
- Server-side configure to allow extension origins
- Use `chrome.identity.getAuthToken()` (optional OAuth)
- API endpoints return appropriate CORS headers

**Data Encryption**
- Local storage uses `chrome.storage.local` (auto-encrypted)
- Sensitive data (notes) optional end-to-end encryption
- HTTPS transport

### 4.3 Offline Queue Mechanism

**Offline Support**
- Store failed API requests to local queue
- Use `chrome.alarms` for periodic retry
- Queue max 100 items, clean oldest when exceeded
- Batch sync when reconnected

**Sync Status Indicators**
- Green: Synced
- Orange: Syncing
- Red: Sync failed
- Gray: Offline

---

## Part 5: Testing Strategy & Implementation Plan

### 5.1 Testing Strategy

**Unit Tests**
- Content Script text selection logic
- Annotation data serialization/deserialization
- Offline queue management
- API client error handling

**Integration Tests**
- Extension → Backend API communication
- Annotation sync complete flow
- Authentication flow
- Cross-domain request handling

**Manual Testing Scenarios**
- Test capture on different sites (GitHub, Wikipedia, Blogs)
- Annotation display on different page types
- Offline/online switching
- Multi-device sync verification

**Browser Compatibility**
- Chrome (primary target)
- Edge (Chromium-based, compatible)
- Firefox (future support)

### 5.2 Implementation Task Breakdown

**Week 1: Basic Framework**
1. Set up Chrome Extension project structure
2. Configure Manifest V3
3. Implement Background Service Worker
4. Create Popup basic UI
5. Implement API key authentication

**Week 2: Content Capture**
1. Implement Content Script text selection detection
2. Floating toolbar UI and interaction
3. Metadata auto-extraction
4. API submit logic
5. Offline queue basic implementation

**Week 3: Annotation Features**
1. Page highlight implementation
2. Note addition feature
3. Annotation local storage
4. Annotation sync API
5. Load annotations when revisiting pages

**Week 4: Polish & Testing**
1. Popup interface refinement
2. Sync status optimization
3. Error handling and user prompts
4. Complete testing
5. Documentation writing
6. Release preparation

### 5.3 File Structure

```
browser-extension/
├── manifest.json
├── background/
│   ├── service-worker.js
│   ├── api-client.js
│   ├── queue-manager.js
│   └── auth-manager.js
├── content/
│   ├── content.js
│   ├── content.css
│   ├── selector.js
│   ├── highlighter.js
│   └── toolbar.js
├── popup/
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── tests/
    ├── content.test.js
    ├── api.test.js
    └── integration.test.js
```

---

## Success Criteria

✅ Users can select text on any webpage and save to knowledge base
✅ Users can highlight and annotate web pages
✅ All captures sync in real-time to server
✅ Offline queue handles network failures gracefully
✅ Extension works on Chrome and Edge
✅ All tests pass
✅ User documentation complete

---

## Next Steps

1. Create detailed implementation plan with tasks
2. Set up isolated git worktree for development
3. Begin Week 1 tasks

**Phase 3 Complete!** 🎉
