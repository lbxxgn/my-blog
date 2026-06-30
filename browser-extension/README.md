# Knowledge Base Browser Extension

Chrome Extension (Manifest V3) for quick content capture and web page annotation, syncing to the Simple Blog knowledge base backend.

## Table of Contents

- [Installation](#installation)
- [Features](#features)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Changelog](#changelog)

---

## Installation

### Development Mode

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `browser-extension` directory
5. Extension should now appear in your toolbar

### Configuration

#### For Local Development

1. Make sure the backend server is running at `http://localhost:5001`
2. Generate an API key:
   ```bash
   cd browser-extension
   python3 generate-api-key.py
   # enter your username (e.g. admin)
   ```
3. Click the extension icon in toolbar
4. Click settings (gear icon ⚙️)
5. Enter your API Key
6. The default API URL is `http://localhost:5001/knowledge_base`; change it only if your backend is on a different origin
7. You're ready to capture!

#### For Remote Server (Production)

**IMPORTANT**: The extension needs permission to access your remote server.

**Option 1: Modify manifest.json (Recommended for Production)**

1. Open `browser-extension/manifest.json`
2. Update the `host_permissions` section:
   ```json
   "host_permissions": [
     "https://your-domain.com/*"
   ]
   ```
3. Reload the extension in Chrome

**Option 2: Use as Development Extension (For Testing)**

The extension comes with `http://localhost:5001/*` permission. To test with a remote server:

1. Click extension icon
2. Click settings (⚙️)
3. Enter your API URL (e.g. `https://blog.example.com/knowledge_base`)
4. Click "Test Connection" to verify
5. Save settings
6. Chrome will prompt for additional permissions - accept them

**Server Setup** (on your server):

1. Deploy the Simple Blog backend to your server
2. Ensure HTTPS is enabled (required for extensions from web store)
3. The plugin API endpoints are already CSRF-exempt and accept `X-API-Key` authentication

---

## Features

- **Quick Capture**: Select text on any webpage, click save button
- **Add Tags**: Save with custom tags for organization
- **Add Notes**: Attach notes to captured content
- **Auto Metadata**: Page title and URL automatically saved
- **Floating Toolbar**: Appears when you select text
- **Visual Feedback**: Notifications show save status

---

## Usage

### Basic Capture

1. Navigate to any webpage
2. Select text with your mouse
3. Click the 📌 button in the floating toolbar
4. Content is saved to your knowledge base!

### Capture with Tags

1. Select text
2. Click the 🏷️ button
3. Enter comma-separated tags (e.g., `python, tutorial, important`)
4. Click OK to save

### Capture with Note

1. Select text
2. Click the ✏️ button
3. Enter your note
4. Content is saved with note attached

---

## API Documentation

The extension communicates with the backend via REST API. All endpoints require API key authentication.

### Base URL

For local development:

```
http://localhost:5001/knowledge_base
```

For production, use your server's origin plus `/knowledge_base`:

```
https://your-domain.com/knowledge_base
```

### Authentication

All API requests must include an `X-API-Key` header:

```javascript
headers: {
  'Content-Type': 'application/json',
  'X-API-Key': 'your-api-key-here'
}
```

### Endpoints

#### 1. Submit Content

Create a new knowledge card from captured content.

**Endpoint:** `POST /knowledge_base/api/plugin/submit`

**Request:**
```json
{
  "title": "Page Title",
  "content": "Selected text content",
  "source_url": "https://example.com/page",
  "url": "https://example.com/page",
  "tags": ["tag1", "tag2"],
  "annotation_type": "capture",
  "create_as_post": false
}
```

**Response (Success - Card):**
```json
{
  "success": true,
  "card_id": 123,
  "type": "card",
  "message": "Saved successfully"
}
```

**Response (Success - Post):**
```json
{
  "success": true,
  "post_id": 456,
  "type": "post",
  "message": "文章创建成功"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message"
}
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (missing required fields)
- `401` - Unauthorized (invalid or missing API key)

#### 2. Sync Annotations

Save page annotations (highlights) to backend.

**Endpoint:** `POST /knowledge_base/api/plugin/sync-annotations`

**Request:**
```json
{
  "url": "https://example.com/page",
  "annotations": [
    {
      "text": "Selected text",
      "xpath": "/html/body/p[1]",
      "color": "yellow",
      "note": "My note",
      "annotation_type": "highlight"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "annotation_ids": [1, 2, 3],
  "count": 3
}
```

#### 3. Get Annotations

Retrieve all annotations for a specific URL.

**Endpoint:** `GET /knowledge_base/api/plugin/annotations?url={url}`

**Response:**
```json
{
  "success": true,
  "annotations": [
    {
      "id": 1,
      "annotation_text": "Selected text",
      "xpath": "/html/body/p[1]",
      "color": "yellow",
      "note": "My note",
      "annotation_type": "highlight",
      "created_at": "2026-03-19T10:00:00"
    }
  ],
  "count": 1
}
```

#### 4. Get Recent Captures

Retrieve recently captured cards.

**Endpoint:** `GET /knowledge_base/api/plugin/recent?limit={10}`

**Response:**
```json
{
  "success": true,
  "cards": [
    {
      "id": 1,
      "title": "标题",
      "content": "内容",
      "tags": ["tag1"],
      "status": "idea",
      "source": "plugin",
      "created_at": "2026-03-19T10:00:00"
    }
  ],
  "count": 10
}
```

---

## Development

### File Structure

```
browser-extension/
├── manifest.json          # Extension configuration (Manifest V3)
├── background/
│   ├── api-client.js      # API client
│   ├── auth-manager.js    # Authentication manager
│   └── service-worker.js  # Service worker (background scripts)
├── content/
│   ├── content-bundle.js  # Injected into web pages (no ES6 imports)
│   ├── content.css        # Styles for injected content
│   ├── content.js
│   ├── selector.js
│   └── toolbar.js         # Floating toolbar
├── popup/
│   ├── popup.html         # Popup interface
│   ├── popup.js           # Popup logic
│   └── popup.css          # Popup styles
├── icons/
│   ├── icon16.png         # 16x16 icon
│   ├── icon48.png         # 48x48 icon
│   └── icon128.png        # 128x128 icon
├── generate-api-key.py    # Utility to generate API keys
├── setup-test.sh          # Verification script
├── TESTING.md             # Testing guide
└── README.md              # This file
```

### Key Implementation Details

1. **No ES6 Modules in Content Scripts**: Chrome doesn't support ES6 imports in content scripts. All code is bundled in `content-bundle.js`.

2. **Service Worker Limitations**: Dynamic imports don't work in Service Workers. All API client code is inlined or bundled in `service-worker.js`.

3. **CSRF Exemption**: Browser extensions can't handle CSRF tokens, so the plugin API endpoints are exempted from CSRF protection.

4. **API Base Path**: The plugin API is registered under the `/knowledge_base` blueprint, so the full local base URL is `http://localhost:5001/knowledge_base`.

5. **Console Logging**: Extensive logging for debugging:
   - 🔑 API key operations
   - 📤 Outgoing requests
   - 📥 Incoming responses
   - ✅ Success messages
   - ❌ Errors

---

## Testing

### Manual Testing

1. Load extension in dev mode
2. Navigate to any webpage
3. Select text and verify toolbar appears
4. Click save button
5. Check backend database for new card:
   ```bash
   sqlite3 db/simple_blog.db "SELECT * FROM cards ORDER BY id DESC LIMIT 5"
   ```

### Automated Testing

The backend has comprehensive tests:

```bash
# Run all tests
pytest tests/ -v

# Run knowledge base related tests
pytest tests/test_knowledge_base.py -v
pytest tests/test_security.py -v
```

---

## Troubleshooting

### Toolbar not appearing?

**Cause:** Extension not loaded or content script failed to inject.

**Solutions:**
- Ensure you've selected text (highlight with mouse)
- Check `chrome://extensions/` for errors
- Open browser console (F12) and look for red errors
- Try reloading the page

### Save failing with "API key not configured"?

**Cause:** No API key in extension storage.

**Solutions:**
1. Click extension icon
2. Click settings (gear icon)
3. Enter your API key
4. Try saving again

### Save failing with "API error: 401"?

**Cause:** Invalid API key.

**Solutions:**
1. Regenerate API key: `python3 generate-api-key.py`
2. Update in extension settings
3. Try again

### Save failing with "API error: 404" or connection refused?

**Cause:** Backend server not running or wrong API URL.

**Solutions:**
1. Start backend server:
   ```bash
   source .venv/bin/activate
   python backend/app.py
   ```
2. Verify API URL in extension settings ends with `/knowledge_base` for local development
3. Verify server is running: `curl http://localhost:5001/knowledge_base/api/plugin/recent?limit=1 -H "X-API-Key: your-key"`

### "No response from extension" error?

**Cause:** Service worker crashed or not responding.

**Solutions:**
1. Go to `chrome://extensions/`
2. Click "Service worker" link to view debug console
3. Look for errors
4. Click "Reload" button for extension

---

## Changelog

### v1.1.0 (Current)

**Updated:**
- Plugin API base URL updated to `/knowledge_base`
- Settings support custom remote API URL
- Popup shows recent captures via `/knowledge_base/api/plugin/recent`

### v1.0.0 (2026-01-31)

**Added:**
- Initial browser extension implementation
- Quick capture functionality
- Tag and note support
- Floating toolbar UI
- API key authentication
- Three plugin API endpoints (submit, sync-annotations, get-annotations)

**Fixed:**
- ES6 module compatibility (bundled content script)
- Service Worker dynamic import limitation
- CSRF token exemption

---

## License

MIT

## Contributing

Issues and PRs are welcome!
