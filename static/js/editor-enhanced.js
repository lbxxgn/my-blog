// Enhanced Editor with EasyMDE integration
document.addEventListener('DOMContentLoaded', function() {
    const textarea = document.getElementById('content');

    if (textarea) {
        // Initialize EasyMDE
        const easyMDE = new EasyMDE({
            element: textarea,
            spellChecker: false,
            autosave: {
                enabled: true,
                delay: 1000,
                submit_delay: 5000,
                time_format: {
                    locale: 'zh-CN',
                    format: '%Y-%m-%d %H:%M:%S'
                },
                text: '自动保存于 '
            },
            placeholder: '开始写作...\n\n支持 Markdown 语法：\n# 标题\n**粗体** 或 *斜体*\n`代码`\n\n- 列表项\n\n> 引用块\n\n[链接文字](url)\n\n![图片描述](url)',
            autofocus: true,
            forceSync: true,
            shortcuts: {
                drawTable: 'Cmd-Opt-T',
                toggleBold: 'Cmd-B',
                toggleItalic: 'Cmd-I',
                drawLink: 'Cmd-K',
                togglePreview: 'Cmd-P',
                toggleSideBySide: 'Cmd-Opt-P',
                toggleFullScreen: 'F11'
            },
            toolbar: [
                'bold',
                'italic',
                'strikethrough',
                'heading',
                '|',
                'quote',
                'unordered-list',
                'ordered-list',
                '|',
                'link',
                'image',
                'table',
                '|',
                'code',
                'inline-code',
                {
                    name: 'upload-image',
                    action: (editor) => {
                        // Trigger image upload
                        document.getElementById('imageUpload').click();
                    },
                    className: 'fa fa-upload',
                    title: '上传图片'
                },
                '|',
                'preview',
                'side-by-side',
                'fullscreen',
                '|',
                'guide',
                '|',
                {
                    name: 'clear',
                    action: (editor) => {
                        if (confirm('确定要清空编辑器吗？此操作不可撤销。')) {
                            editor.value('');
                            editor.codemirror.refresh();
                        }
                    },
                    className: 'fa fa-trash',
                    title: '清空'
                }
            ],
            insertTexts: {
                horizontalRule: [
                    {
                        name: '分割线',
                        action: (editor) => {
                            editor.codemirror.replaceSelection('---\n');
                        }
                    }
                ],
                image: [
                    {
                        name: '上传图片',
                        action: (editor) => {
                            document.getElementById('imageUpload').click();
                        }
                    }
                ]
            },
            promptURLs: {
                uploadImage: '/admin/upload'
            },
            previewClass: 'editor-preview',
            statusbar: ['autosave', 'lines', 'words', 'cursor'],
            maxHeight: '500px',
            renderingConfig: {
                singleLineBreaks: false,
                codeSyntaxHighlighting: true
            },
            previewImagesInEditor: true,
            syncScroll: true,
            lineNumbers: true
        });

        // Get CSRF token for image upload
        const csrfToken = document.querySelector('meta[name="csrf_token"]')
            ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
            : '';

        // Custom image upload handler
        easyMDE.imageUploadEndpoint = '/admin/upload';

        easyMDE.imageUploadFunction = function(file, onSuccess, onError) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('csrf_token', csrfToken);

            fetch('/admin/upload', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    onSuccess(data.url);
                } else {
                    onError(data.error);
                }
            })
            .catch(error => {
                onError('上传失败: ' + error.message);
            });
        };

        // Handle form submission
        const form = document.getElementById('editorForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                // Ensure EasyMDE content is synced
                easyMDE.codemirror.save();
            });
        }

        // Auto-save functionality
        const saveStatus = document.getElementById('saveStatus');
        if (saveStatus) {
            let autoSaveTimeout;

            // Listen for changes
            easyMDE.codemirror.on('change', function() {
                clearTimeout(autoSaveTimeout);
                saveStatus.textContent = '正在保存...';
                saveStatus.className = 'save-status saving';

                autoSaveTimeout = setTimeout(function() {
                    // Save to localStorage
                    localStorage.setItem('editor_content', easyMDE.value());
                    saveStatus.textContent = '已自动保存 ' + new Date().toLocaleTimeString();
                    saveStatus.className = 'save-status saved';
                }, 1000);
            });

            // Load saved content on page load
            const savedContent = localStorage.getItem('editor_content');
            if (savedContent && !textarea.value) {
                if (confirm('发现未保存的草稿，是否恢复？')) {
                    easyMDE.value(savedContent);
                }
            }
        }

        // Custom button handlers
        const publishToggle = document.getElementById('publishToggle');
        const isPublishedCheckbox = document.getElementById('is_published');

        window.togglePublish = function() {
            if (publishToggle && isPublishedCheckbox) {
                isPublishedCheckbox.checked = true;
                // Submit form after a short delay to allow checkbox to be set
                setTimeout(() => {
                    form.submit();
                }, 100);
            }
        };

        // Keyboard shortcuts for fullscreen
        document.addEventListener('keydown', function(e) {
            if (e.key === 'F11') {
                e.preventDefault();
                easyMDE.toggleFullScreen();
            }
        });

        // Window resize handler
        window.addEventListener('resize', function() {
            if (document.fullscreenElement) {
                // Adjust editor height in fullscreen
                const editorContainer = document.querySelector('.admin-editor');
                if (editorContainer) {
                    editorContainer.style.height = window.innerHeight + 'px';
                }
            }
        });
    }
});

// Image upload handler (outside EasyMDE init)
const imageUpload = document.getElementById('imageUpload');
if (imageUpload) {
    imageUpload.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        const csrfToken = document.querySelector('meta[name="csrf_token"]')
            ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
            : '';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('csrf_token', csrfToken);

        try {
            const saveStatus = document.getElementById('saveStatus');
            if (saveStatus) {
                saveStatus.textContent = '正在上传图片...';
                saveStatus.className = 'save-status saving';
            }

            const response = await fetch('/admin/upload', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Insert markdown into EasyMDE
                const easyMDE = document.querySelector('.EasyMDEContainer').EasyMDE;
                const cm = easyMDE.codemirror;
                const cursor = cm.getCursor();

                const markdown = `![${file.name.split('.')[0] || '图片'}](${data.url})`;
                cm.replaceRange(markdown, cursor);

                if (saveStatus) {
                    saveStatus.textContent = '图片上传成功！';
                    saveStatus.className = 'save-status saved';
                    setTimeout(() => {
                        saveStatus.textContent = '';
                        saveStatus.className = 'save-status';
                    }, 2000);
                }
            } else {
                if (saveStatus) {
                    saveStatus.textContent = '上传失败: ' + data.error;
                    saveStatus.className = 'save-status error';
                    setTimeout(() => {
                        saveStatus.textContent = '';
                        saveStatus.className = 'save-status';
                    }, 3000);
                } else {
                    alert('上传失败: ' + data.error);
                }
            }
        } catch (error) {
            if (saveStatus) {
                saveStatus.textContent = '上传失败: ' + error.message;
                saveStatus.className = 'save-status error';
                setTimeout(() => {
                    saveStatus.textContent = '';
                    saveStatus.className = 'save-status';
                }, 3000);
            } else {
                alert('上传失败: ' + error.message);
            }
        }

        // Reset file input
        e.target.value = '';
    });
}
