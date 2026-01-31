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

1. Make sure the backend server is running at `http://localhost:5001`
2. Generate an API key:
   ```bash
   cd browser-extension
   python3 generate-api-key.py
   ```
3. Click the extension icon in toolbar
4. Click settings (gear icon ⚙️)
5. Enter your API Key
6. You're ready to capture!

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
```
http://localhost:5001
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

**Endpoint:** `POST /api/plugin/submit`

**Request:**
```json
{
  "title": "Page Title",
  "content": "Selected text content",
  "source_url": "https://example.com/page",
  "tags": ["tag1", "tag2"],
  "annotation_type": "capture"
}
```

**Response (Success):**
```json
{
  "success": true,
  "card_id": 123,
  "message": "Saved successfully"
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

**Endpoint:** `POST /api/plugin/sync-annotations`

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

**Endpoint:** `GET /api/plugin/annotations?url={url}`

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
      "created_at": "2026-01-31 12:00:00"
    }
  ],
  "count": 1
}
```

---

## Development

### File Structure

```
browser-extension/
├── manifest.json          # Extension configuration (Manifest V3)
├── background/
│   └── service-worker.js # Service worker (background scripts)
├── content/
│   ├── content-bundle.js # Injected into web pages (no ES6 imports)
│   └── content.css       # Styles for injected content
├── popup/
│   ├── popup.html        # Popup interface
│   ├── popup.js          # Popup logic
│   └── popup.css         # Popup styles
├── icons/
│   ├── icon16.png        # 16x16 icon
│   ├── icon48.png        # 48x48 icon
│   └── icon128.png       # 128x128 icon
├── generate-api-key.py   # Utility to generate API keys
├── setup-test.sh         # Verification script
├── TESTING.md            # Testing guide
└── README.md             # This file
```

### Key Implementation Details

1. **No ES6 Modules in Content Scripts**: Chrome doesn't support ES6 imports in content scripts. All code is bundled in `content-bundle.js`.

2. **Service Worker Limitations**: Dynamic imports don't work in Service Workers. All API client code is inlined in `service-worker.js`.

3. **CSRF Exemption**: Browser extensions can't handle CSRF tokens, so the plugin API endpoints are exempted from CSRF protection.

4. **Console Logging**: Extensive logging for debugging:
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
   ```python
   # In backend directory
   sqlite3 db/simple_blog.db "SELECT * FROM cards ORDER BY id DESC LIMIT 5"
   ```

### Automated Testing

The backend has comprehensive tests:

```bash
# Run all tests
pytest tests/ -v

# Run only knowledge base tests
pytest tests/test_routes.py::TestKnowledgeBaseRoutes -v
pytest tests/test_models.py::TestKnowledgeBaseModels -v
```

**Test Coverage:**
- 66 total tests (all passing)
- 9 plugin API route tests
- 16 knowledge base model tests

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

**Cause:** Backend server not running.

**Solutions:**
1. Start backend server:
   ```bash
   cd backend
   export ADMIN_USERNAME='admin'
   export ADMIN_PASSWORD='AdminPass123!'
   python3 app.py
   ```
2. Verify server is running: `curl http://localhost:5001/`

### "No response from extension" error?

**Cause:** Service worker crashed or not responding.

**Solutions:**
1. Go to `chrome://extensions/`
2. Click "Service worker" link to view debug console
3. Look for errors
4. Click "Reload" button for extension

---

## Changelog

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

**Known Issues:**
- No offline queue (requests fail if backend unavailable)
- Hardcoded API URL (localhost:5001 only)
- Popup "Recent Captures" not implemented (needs backend endpoint)

---

## License

MIT

## Contributing

Contributions welcome! Please see [CODE_REVIEW_2026-01-31.md](../docs/CODE_REVIEW_2026-01-31.md) for known issues and improvement suggestions.
