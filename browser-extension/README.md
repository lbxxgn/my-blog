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
