// Markdown preview functionality
const contentTextarea = document.getElementById('content');
const previewDiv = document.getElementById('preview');

if (contentTextarea && previewDiv) {
    // Simple Markdown to HTML converter
    function parseMarkdown(text) {
        let html = text
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            // Code
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            // Links
            .replace(/\[([^\]]+)\]\(([^\)]+)\)/gim, '<a href="$2">$1</a>')
            // Images
            .replace(/!\[([^\]]*)\]\(([^\)]+)\)/gim, '<img src="$2" alt="$1">')
            // Line breaks
            .replace(/\n/gim, '<br>');

        return html;
    }

    // Update preview on input
    contentTextarea.addEventListener('input', function() {
        previewDiv.innerHTML = parseMarkdown(this.value);
    });

    // Initial preview
    previewDiv.innerHTML = parseMarkdown(contentTextarea.value);

    // Insert Markdown syntax
    window.insertMarkdown = function(before, after) {
        const start = contentTextarea.selectionStart;
        const end = contentTextarea.selectionEnd;
        const text = contentTextarea.value;
        const selectedText = text.substring(start, end);

        contentTextarea.value = text.substring(0, start) + before + selectedText + after + text.substring(end);
        contentTextarea.focus();
        contentTextarea.selectionStart = start + before.length;
        contentTextarea.selectionEnd = start + before.length + selectedText.length;

        // Trigger input event to update preview
        contentTextarea.dispatchEvent(new Event('input'));
    };
}

// Image upload functionality
const imageUpload = document.getElementById('imageUpload');
if (imageUpload) {
    imageUpload.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/admin/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Insert image Markdown at cursor position
                const markdown = `![图片描述](${data.url})`;
                const textarea = document.getElementById('content');
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;

                textarea.value = textarea.value.substring(0, start) + markdown + textarea.value.substring(end);
                textarea.focus();
                textarea.selectionStart = textarea.selectionEnd = start + markdown.length;

                // Trigger input event to update preview
                textarea.dispatchEvent(new Event('input'));
            } else {
                alert('上传失败: ' + data.error);
            }
        } catch (error) {
            alert('上传失败: ' + error.message);
        }

        // Reset file input
        e.target.value = '';
    });
}
