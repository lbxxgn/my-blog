/* ────────────────────────────────────────────────────────────────
   快捷键基础设施

   约定：
   - mod = ⌘（macOS）/ Ctrl（Windows、Linux）。旧实现把 ⌃ 与 ⌘ 视作同一个键，
     导致 macOS 上按 Control 组合也会触发站内快捷键，也无法表达 ⌘ 语义。
   - 系统/浏览器保留键一律放行（见 RESERVED_COMBOS），不做拦截。
   - 焦点在输入框/可编辑区域时不触发，除非显式声明 allowInEditable。
   - 刻意不注册的键：⌘N ⌘T ⌘W ⌘P ⌘F ⌘R ⌘⇧S ⌘⇧T ⌘D ⌘B ⌘I ⌘K(编辑器内)。
   ──────────────────────────────────────────────────────────────── */
var isMacPlatform = /Mac|iPhone|iPad|iPod/.test(
    (navigator.platform || '') + ' ' + (navigator.userAgent || '')
);

// 命中即放行给浏览器，避免抢掉刷新/打印/查找/恢复标签页等系统行为
var RESERVED_COMBOS = [
    'mod+r', 'mod+shift+r',
    'mod+n', 'mod+t', 'mod+w', 'mod+q',
    'mod+p', 'mod+shift+p',
    'mod+f', 'mod+g', 'mod+shift+g',
    'mod+shift+t',
    'mod+shift+s',
    'mod+d', 'mod+shift+d',
    'mod+l', 'mod+o', 'mod+shift+o'
];

class ShortcutHandler {
    constructor() {
        this.shortcuts = new Map();
        this.init();
    }

    init() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    register(key, callback, description = '', options = {}) {
        this.shortcuts.set(key.toLowerCase(), {
            callback: callback,
            description: description,
            allowInEditable: !!options.allowInEditable
        });
    }

    isEditableTarget(target) {
        if (!target) return false;
        const tag = (target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
        if (target.isContentEditable) return true;
        return !!(target.closest && target.closest('[contenteditable="true"]'));
    }

    handleKeyDown(e) {
        const key = this.getKeyString(e);
        // 未注册的组合直接放行，不 preventDefault（保证浏览器原生行为可用）
        if (RESERVED_COMBOS.indexOf(key) !== -1) return;
        const shortcut = this.shortcuts.get(key);
        if (!shortcut) return;
        if (!shortcut.allowInEditable && this.isEditableTarget(e.target)) return;
        e.preventDefault();
        e.stopPropagation();
        shortcut.callback(e);
    }

    // ⌘（macOS）/ Ctrl（其他）统一归一化为 mod；⌃ 在 macOS 上单独记为 ctrl
    getKeyString(e) {
        const parts = [];
        if (isMacPlatform) {
            if (e.metaKey) parts.push('mod');
            if (e.ctrlKey) parts.push('ctrl');
        } else if (e.ctrlKey) {
            parts.push('mod');
        }
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');

        let key = String(e.key || '').toLowerCase();
        const keyMap = {
            ' ': 'space', 'escape': 'esc',
            'arrowup': 'up', 'arrowdown': 'down',
            'arrowleft': 'left', 'arrowright': 'right'
        };
        if (keyMap[key]) key = keyMap[key];
        parts.push(key);
        return parts.join('+');
    }

    getShortcuts() {
        const list = [];
        this.shortcuts.forEach(function (value, key) {
            if (!value.description) return;
            list.push({ key: shortcutHandler.formatKey(key), description: value.description });
        });
        return list;
    }

    // 显示用：macOS 用 ⌘ ⌃ ⌥ ⇧，其他平台用 Ctrl / Alt / Shift
    formatKey(key) {
        const tokens = key.split('+');
        const labels = tokens.map(function (token) {
            if (token === 'mod') return isMacPlatform ? '⌘' : 'Ctrl';
            if (token === 'ctrl') return isMacPlatform ? '⌃' : 'Ctrl';
            if (token === 'alt') return isMacPlatform ? '⌥' : 'Alt';
            if (token === 'shift') return isMacPlatform ? '⇧' : 'Shift';
            if (token === 'esc') return 'Esc';
            if (token === 'space') return 'Space';
            if (token === 'up') return '↑';
            if (token === 'down') return '↓';
            if (token.length === 1) return token.toUpperCase();
            return token.charAt(0).toUpperCase() + token.slice(1);
        });
        return labels.join(isMacPlatform ? '' : '+');
    }
}

const shortcutHandler = new ShortcutHandler();

document.addEventListener('DOMContentLoaded', function () {
    const currentPage = document.body.dataset.page || 'home';
    const inEditor = currentPage === 'editor';

    // ⌘K / Ctrl+K：命令面板。编辑器内不注册，把 ⌘K 留给 Quill 的「插入链接」。
    if (!inEditor) {
        shortcutHandler.register('mod+k', function () {
            const ua = navigator.userAgent || '';
            const mobile = /iPhone|iPad|Android|webOS|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua) ||
                (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) ||
                window.innerWidth < 768;
            if (mobile) {
                window.location.href = '/search';
                return;
            }
            // 未登录时命令面板不可用（搜索需要权限），退化为聚焦顶栏搜索框
            const canUsePalette = !!(document.getElementById('themeToggleNav') ||
                document.querySelector('.nav-links .dropdown .user-icon'));
            if (!canUsePalette || !window.CommandPalette) {
                const input = document.querySelector('.search-input-nav');
                if (input && input.offsetParent !== null) {
                    input.focus();
                    input.select();
                } else {
                    window.location.href = '/search';
                }
                return;
            }
            if (window.CommandPalette.isOpen && window.CommandPalette.isOpen()) {
                window.CommandPalette.close();
            } else {
                window.CommandPalette.open();
            }
        }, '打开命令面板', { allowInEditable: true });
    }

    shortcutHandler.register('mod+/', showShortcutHelp, '显示快捷键帮助', { allowInEditable: true });

    if (inEditor) {
        registerEditorShortcuts();
    } else if (currentPage === 'quick_note') {
        registerQuickNoteShortcuts();
    }
});

function registerEditorShortcuts() {
    // ⌘S / Ctrl+S：保存。拦住浏览器「保存网页」，并让「更新」「保存草稿」都可用。
    shortcutHandler.register('mod+s', function () {
        const saveBtn = document.getElementById('saveBtn') ||
            document.querySelector('#editorForm button[type="submit"]');
        if (saveBtn) {
            saveBtn.click();
            return;
        }
        const form = document.getElementById('editorForm');
        if (form && form.requestSubmit) form.requestSubmit();
    }, '保存文章', { allowInEditable: true });

    // 说明：加粗/斜体等格式快捷键交给 Quill 原生实现（⌘B、⌘I、⌘U），
    // 这里不再注册 execCommand 版本，避免同一次按键被执行两次。
    // 原先的 ⌘P（预览）、⌘⇧S（另存为）、⌘⇧T（恢复标签页）、⌃⌥L/O 均已移除。
}

function registerQuickNoteShortcuts() {
    shortcutHandler.register('mod+s', function () {
        const form = document.getElementById('quick-note-form');
        if (!form) return;
        if (form.requestSubmit) {
            form.requestSubmit();
        } else {
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    }, '保存笔记', { allowInEditable: true });
}

function registerAdminShortcuts() {}

function registerTimelineShortcuts() {}
function togglePreview(){const previewPane=document.querySelector('.preview-pane');if(previewPane){previewPane.classList.toggle('active');}else{createPreviewPane();}}
function createPreviewPane(){const editorContainer=document.querySelector('.admin-editor');if(!editorContainer)return;if(document.querySelector('.preview-pane'))return;const editorPane=editorContainer.querySelector('.editor-form');const previewPane=document.createElement('div');previewPane.className='preview-pane';previewPane.innerHTML=`<div class="preview-header"><h3>预览</h3><button class="close-preview"onclick="togglePreview()">×</button></div><div class="preview-content"id="previewContent"></div>`;editorContainer.insertBefore(previewPane,editorPane);updatePreview();const titleInput=document.getElementById('title');const contentTextarea=document.getElementById('content');if(titleInput){titleInput.addEventListener('input',debounce(updatePreview,300));}
if(contentTextarea){contentTextarea.addEventListener('input',debounce(updatePreview,300));}}
function updatePreview(){const title=document.getElementById('title').value;const content=document.getElementById('content').value;const previewContent=document.getElementById('previewContent');if(previewContent){const html=markdownToHTML(content);previewContent.innerHTML=`<h1>${title||'（无标题）'}</h1>${html}`;}}
function markdownToHTML(markdown){if(!markdown)return'';return markdown
.replace(/^# (.+)$/gm,'<h1>$1</h1>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^#### (.+)$/gm,'<h4>$1</h4>')
.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\*(.+?)\*/g,'<em>$1</em>')
.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2">$1</a>')
.replace(/`([^`]+)`/g,'<code>$1</code>').replace(/```([\s\S]*?)```/g,'<pre><code>$1</code></pre>')
.replace(/\n\n/g,'</p><p>').replace(/^/,'<p>').replace(/$/,'</p>');}
function showShortcutHelp(){
  const shortcuts = shortcutHandler.getShortcuts();
  const mod = isMacPlatform ? '⌘' : 'Ctrl';
  const modal = document.createElement('div');
  modal.className = 'shortcut-help-modal';
  modal.innerHTML = '<div class="modal-content">' +
    '<div class="modal-header"><h2>键盘快捷键</h2>' +
    '<button class="close-modal" aria-label="关闭">×</button></div>' +
    '<div class="modal-body">' +
    '<table class="shortcut-table"><thead><tr><th>快捷键</th><th>说明</th></tr></thead><tbody>' +
    shortcuts.map(function (s) { return '<tr><td><code>' + s.key + '</code></td><td>' + s.description + '</td></tr>'; }).join('') +
    '</tbody></table>' +
    '<div class="shortcut-note"><p><strong>说明</strong></p><ul>' +
    '<li>本表只列出当前页面可用的组合</li>' +
    '<li>' + (isMacPlatform ? '<code>⌘</code> 为 Command，<code>⌥</code> 为 Option' : '<code>Ctrl</code> 对应 Windows / Linux') + '</li>' +
    '<li>浏览器与系统保留键（刷新、打印、查找、恢复标签页等）不会被拦截</li>' +
    '</ul></div></div></div>';

  function close() {
    document.removeEventListener('keydown', onKeyDown, true);
    modal.remove();
  }
  function onKeyDown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
    }
  }

  document.body.appendChild(modal);
  document.addEventListener('keydown', onKeyDown, true);
  modal.addEventListener('click', function (e) {
    if (e.target === modal) close();
  });
  modal.querySelector('.close-modal').addEventListener('click', close);
}
function debounce(func,wait){let timeout;return function executedFunction(...args){const later=()=>{clearTimeout(timeout);func(...args);};clearTimeout(timeout);timeout=setTimeout(later,wait);};}
function showNotification(message,type='info'){const notification=document.createElement('div');notification.className=`notification notification-${type}`;notification.textContent=message;notification.style.cssText=`position:fixed;top:20px;right:20px;padding:12px 20px;background:${type==='success'?'#d4edda':type==='error'?'#f8d7da':'#d1ecf1'};color:${type==='success'?'#155724':type==='error'?'#721c24':'#0c5460'};border-radius:6px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:10000;animation:slideIn 0.3s ease-out;`;document.body.appendChild(notification);setTimeout(()=>{notification.style.animation='slideOut 0.3s ease-out';setTimeout(()=>notification.remove(),300);},3000);}
const style=document.createElement('style');style.textContent=`@keyframes slideIn{from{transform:translateX(100%);opacity:0;}
to{transform:translateX(0);opacity:1;}}@keyframes slideOut{from{transform:translateX(0);opacity:1;}
to{transform:translateX(100%);opacity:0;}}.shortcut-help-modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:9999;}.shortcut-help-modal.modal-content{background:var(--card-bg,#fff);border-radius:12px;max-width:600px;width:90%;max-height:80vh;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.3);}.shortcut-help-modal.modal-header{display:flex;justify-content:space-between;align-items:center;padding:20px;border-bottom:1px solid var(--border-color,#e5e7eb);}.shortcut-help-modal.modal-header h2{margin:0;font-size:1.5rem;}.shortcut-help-modal.close-modal{background:none;border:none;font-size:1.5rem;cursor:pointer;padding:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;}.shortcut-help-modal.modal-body{padding:20px;overflow-y:auto;max-height:calc(80vh-80px);}.shortcut-table{width:100%;border-collapse:collapse;}.shortcut-table th,.shortcut-table td{padding:12px;text-align:left;border-bottom:1px solid var(--border-color,#e5e7eb);}.shortcut-table th{background:var(--code-bg,#f9fafb);font-weight:600;}.shortcut-table code{background:var(--code-bg,#f3f4f6);padding:4px 8px;border-radius:4px;font-family:monospace;font-size:0.9em;}.shortcut-note{margin-top:20px;padding:15px;background:var(--code-bg,#f9fafb);border-radius:8px;}.shortcut-note ul{margin:10px 0 0 0;padding-left:20px;}.shortcut-note li{margin:5px 0;}
.preview-pane{flex:1;background:var(--card-bg,#fff);border-left:1px solid var(--border-color,#e5e7eb);display:none;}.preview-pane.active{display:block;}.preview-header{display:flex;justify-content:space-between;align-items:center;padding:15px 20px;border-bottom:1px solid var(--border-color,#e5e7eb);}.preview-header h3{margin:0;font-size:1.1rem;}.preview-header.close-preview{background:none;border:none;font-size:1.5rem;cursor:pointer;padding:0;}.preview-content{padding:20px;max-height:calc(100vh-200px);overflow-y:auto;}.preview-content h1,.preview-content h2,.preview-content h3,.preview-content h4{margin-top:1.5em;margin-bottom:0.5em;}.preview-content p{line-height:1.6;margin-bottom:1em;}.preview-content code{background:var(--code-bg,#f3f4f6);padding:2px 6px;border-radius:3px;}.preview-content pre{background:var(--code-bg,#f3f4f6);padding:15px;border-radius:6px;overflow-x:auto;}.preview-content a{color:var(--primary-color,#007bff);text-decoration:none;}.preview-content a:hover{text-decoration:underline;}`;document.head.appendChild(style);class ShortcutHint{constructor(){this.hintElement=null;this.autoFadeTimer=null;this.init();}
init(){if(window.location.search.includes('debug=1')){console.log('=== 快捷键调试信息 ===');console.log('用户代理:',navigator.userAgent);console.log('屏幕宽度:',window.innerWidth);console.log('触摸支持:','ontouchstart'in window);console.log('最大触摸点:',navigator.maxTouchPoints);console.log('检测为移动设备:',this.isMobileDevice());console.log('======================');}
if(this.isMobileDevice()){console.log('✓ 检测到移动设备，已隐藏快捷键提示');return;}
if(sessionStorage.getItem('shortcutHintDismissed')==='true'){return;}
this.createHintElement();this.show();}
isMobileDevice(){const userAgent=navigator.userAgent||navigator.vendor||window.opera;if(/iPhone/.test(userAgent)){return true;}
if(/iPad/.test(userAgent)||(/Macintosh/.test(userAgent)&&navigator.maxTouchPoints>1)){return true;}
const mobileRegex=/Android|webOS|iPod|BlackBerry|IEMobile|Opera Mini/i;if(mobileRegex.test(userAgent)){return true;}
if(window.innerWidth&&window.innerWidth<768){return true;}
const hasTouchScreen=('ontouchstart'in window||navigator.maxTouchPoints>0||navigator.msMaxTouchPoints>0);if(hasTouchScreen&&window.innerWidth<1024){return true;}
return false;}
createHintElement(){const hint=document.createElement('div');hint.id='shortcutHint';hint.className='shortcut-hint';hint.innerHTML=`<div class="hint-header"><span>⌨️ 快捷键提示</span><button class="hint-close"onclick="window.shortcutHint.hide()">×</button></div><div class="hint-body">${this.getCurrentPageShortcuts()}</div>`;document.body.appendChild(hint);this.hintElement=hint;}
getCurrentPageShortcuts(){
  const mod = isMacPlatform ? '⌘' : 'Ctrl';
  const pageType = document.body.dataset.page || 'home';
  const table = {
    home: [{ keys: [mod, 'K'], desc: '快速搜索' }, { keys: [mod, '/'], desc: '全部快捷键' }],
    editor: [{ keys: [mod, 'S'], desc: '保存文章' }, { keys: [mod, '/'], desc: '全部快捷键' }],
    admin: [{ keys: [mod, 'K'], desc: '快速搜索' }, { keys: [mod, '/'], desc: '全部快捷键' }]
  };
  const items = table[pageType] || table.home;
  return items.map(function (s) {
    return '<div class="hint-item">' + s.keys.map(function (k) { return '<kbd>' + k + '</kbd>'; }).join(' ') +
      '<span>' + s.desc + '</span></div>';
  }).join('');
}
show(){if(!this.hintElement)return;this.hintElement.style.display='block';this.autoFadeTimer=setTimeout(()=>{this.hide();},3000);}
hide(){if(!this.hintElement)return;if(this.autoFadeTimer){clearTimeout(this.autoFadeTimer);this.autoFadeTimer=null;}
this.hintElement.style.opacity='0';setTimeout(()=>{if(this.hintElement){this.hintElement.style.display='none';}},300);sessionStorage.setItem('shortcutHintDismissed','true');}}
document.addEventListener('DOMContentLoaded',()=>{window.shortcutHint=new ShortcutHint();});