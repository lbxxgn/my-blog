#!/bin/bash
# Browser Extension Test Setup Script

echo "================================"
echo "Browser Extension Test Setup"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "manifest.json" ]; then
    echo "❌ Error: Please run this script from the browser-extension directory"
    echo "   cd browser-extension"
    echo "   ./setup-test.sh"
    exit 1
fi

# Step 1: Verify icon files
echo "📁 Step 1: Verifying icon files..."
if [ -f "icons/icon16.png" ] && [ -f "icons/icon48.png" ] && [ -f "icons/icon128.png" ]; then
    echo "✅ All icon files present"
else
    echo "❌ Missing icon files"
    exit 1
fi

# Step 2: Verify manifest
echo ""
echo "📄 Step 2: Verifying manifest.json..."
if grep -q "manifest_version.*3" manifest.json; then
    echo "✅ Manifest V3 detected"
else
    echo "❌ Invalid manifest"
    exit 1
fi

# Step 3: Check critical files
echo ""
echo "📂 Step 3: Checking required files..."
required_files=(
    "manifest.json"
    "background/service-worker.js"
    "background/api-client.js"
    "content/content.js"
    "content/selector.js"
    "content/toolbar.js"
    "popup/popup.html"
    "popup/popup.js"
)

all_present=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (MISSING)"
        all_present=false
    fi
done

if [ "$all_present" = false ]; then
    echo ""
    echo "❌ Some required files are missing"
    exit 1
fi

# Step 4: Check backend
echo ""
echo "🔧 Step 4: Checking backend server..."
if curl -s http://localhost:5001 > /dev/null 2>&1; then
    echo "✅ Backend server is running on http://localhost:5001"
else
    echo "⚠️  Backend server not detected"
    echo "   Start it with: cd ../backend && python3 app.py"
fi

# Step 5: Instructions
echo ""
echo "================================"
echo "✅ Extension is ready to test!"
echo "================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Open Chrome and go to: chrome://extensions/"
echo "2. Enable 'Developer mode' (top right toggle)"
echo "3. Click 'Load unpacked'"
echo "4. Select this directory: $(pwd)"
echo ""
echo "Don't forget to:"
echo "- Start the backend server: cd ../backend && python3 app.py"
echo "- Get an API key (see TESTING.md for instructions)"
echo "- Configure API key in extension settings"
echo ""
echo "For detailed testing instructions, see: TESTING.md"
echo ""
