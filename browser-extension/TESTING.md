# Browser Extension Testing Guide

## Prerequisites

Before testing the extension, ensure you have:

1. **Chrome or Edge browser** (Manifest V3 supported)
2. **Backend server running** on `http://localhost:5001`
3. **A valid API key** from the knowledge base

## Step 1: Start the Backend Server

```bash
# From the project root
cd backend
python3 app.py
```

Verify the server is running by visiting `http://localhost:5001`

## Step 2: Get or Create an API Key

You need an API key to use the extension. Here's how to get one:

### Option A: From Python Shell

```bash
cd backend
python3
```

```python
from models import get_user_by_username, generate_api_key

# Get your user
user = get_user_by_username('your_username')
user_id = user['id']

# Generate API key
api_key = generate_api_key(user_id)
print(f"Your API key: {api_key}")
```

### Option B: Direct Database Query

```bash
sqlite3 blog.db
```

```sql
-- Find your user ID
SELECT id, username FROM users;

-- Generate an API key (replace USER_ID)
INSERT INTO api_keys (user_id, api_key, created_at)
VALUES (USER_ID, 'your-api-key-here', CURRENT_TIMESTAMP);

-- Verify
SELECT * FROM api_keys;
```

## Step 3: Load the Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Navigate to and select the `browser-extension` directory
5. The extension should now appear in your extensions list!

## Step 4: Configure the Extension

1. Click the extension icon in your browser toolbar
2. You'll see a status indicator (red = not configured, green = configured)
3. Click the **Settings (⚙️)** button
4. Paste your API key when prompted
5. The status should turn green

## Step 5: Test Content Capture

1. Navigate to any webpage (e.g., `https://example.com`)
2. **Select some text** with your mouse
3. A floating toolbar should appear with buttons: 📌 🏷️ ✏️ ❌
4. Click the **📌 (Save)** button
5. You should see a notification: "✅ Saved to knowledge base!"

## Step 6: Verify in Backend

Check that the content was saved:

```bash
sqlite3 blog.db
```

```sql
-- View saved cards
SELECT id, title, substr(content, 1, 50) as content_preview,
       source, created_at
FROM cards
ORDER BY created_at DESC
LIMIT 5;
```

Or visit `http://localhost:5001` if your knowledge base has a web interface.

## Step 7: Test Advanced Features

### Save with Tags

1. Select text on a webpage
2. Click **🏷️ (Save with Tags)** button
3. Enter tags (comma-separated): `test, article, important`
4. Content should be saved with tags

### Save with Note

1. Select text on a webpage
2. Click **✏️ (Save with Note)** button
3. Enter a note: "This is important!"
4. Content should be saved with your note attached

## Troubleshooting

### Toolbar Not Appearing

**Problem:** Floating toolbar doesn't show when selecting text

**Solutions:**
- Make sure you've actually selected (highlighted) text with your mouse
- Open browser DevTools (F12) → Console tab and check for errors
- Try refreshing the page
- Make sure the extension is enabled in `chrome://extensions/`

### Save Failing with Error

**Problem:** Clicking save shows error notification

**Solutions:**
1. Check API key is configured:
   - Click extension icon → Settings
   - Status should be green (not red)

2. Verify backend is running:
   - Visit `http://localhost:5001` in browser
   - Should see your application or an API response

3. Check browser console (F12) for detailed error messages:
   - Look for red error messages
   - Note the specific error code or message

4. Verify API key is valid:
   ```python
   from models import validate_api_key
   validate_api_key('your-api-key-here')
   # Should return user_id, not None
   ```

### Extension Not Loading

**Problem:** Extension fails to load or shows errors

**Solutions:**
1. Check for manifest errors in `chrome://extensions/`
2. Look for detailed error messages in the extension card
3. Try removing and re-adding the extension
4. Check browser console for JavaScript errors

## Debug Mode

For more detailed logging:

1. Open `chrome://extensions/`
2. Find "Knowledge Base Extension"
3. Click "Errors" button to see any errors
4. Click "Inspect" to open DevTools for:
   - Background service worker logs
   - Popup console
   - Content script logs

## Test Checklist

Use this checklist to verify all features work:

- [ ] Extension loads without errors
- [ ] API key can be configured
- [ ] Status indicator shows green (connected)
- [ ] Text selection triggers toolbar appearance
- [ ] Save button (📌) works
- [ ] Save with tags (🏷️) works
- [ ] Save with note (✏️) works
- [ ] Content appears in database
- [ ] Quick note button opens knowledge base
- [ ] Settings dialog can update API key

## Next Steps After Testing

Once testing is complete:

1. **Report any issues** found during testing
2. **Suggest improvements** for UI/UX
3. **Test on different websites** to ensure compatibility
4. **Test on different browsers** (Chrome, Edge, Brave, etc.)

## Manual Testing Script

For systematic testing, follow this script:

1. **Test on Wikipedia:**
   - Go to `https://en.wikipedia.org/wiki/Knowledge`
   - Select first paragraph
   - Save with tag: `wiki, knowledge`
   - Verify save worked

2. **Test on News Site:**
   - Go to any news article
   - Select a quote
   - Save with note: "Interesting perspective"
   - Verify save worked

3. **Test on Technical Docs:**
   - Go to any documentation site
   - Select a code snippet
   - Save with tag: `code, reference`
   - Verify save worked

4. **Test Multiple Selections:**
   - On same page, select and save 3 different sections
   - Verify all 3 were saved correctly

Happy Testing! 🎉
