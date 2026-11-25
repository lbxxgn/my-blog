import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { KbEditorApp } from './KbEditorApp';
import { EditorInitData } from './types';
import './styles/kb-editor.css';

/**
 * 从模板里的 <script type="application/json" id="kb-editor-init"> 读取初始数据。
 * 原来由模板内联脚本解析再挂到 window 上，移到这里可以在不内联脚本的前提下
 * 保持 tests/e2e_kb_editor.py 里 `window.__KB_EDITOR_INIT__` 的用法不变。
 */
function readInitData(): EditorInitData | undefined {
  if (window.__KB_EDITOR_INIT__) return window.__KB_EDITOR_INIT__;

  const el = document.getElementById('kb-editor-init');
  if (!el || !el.textContent) return undefined;

  try {
    window.__KB_EDITOR_INIT__ = JSON.parse(el.textContent);
  } catch (error) {
    console.error('Failed to parse editor init data:', error);
    window.__KB_EDITOR_INIT__ = {} as EditorInitData;
  }
  return window.__KB_EDITOR_INIT__;
}

function init() {
  const container = document.getElementById('kb-editor-root');
  if (!container) {
    console.error('kb-editor-root not found');
    return;
  }

  const initData = (readInitData() || {}) as EditorInitData;
  const root = createRoot(container);
  root.render(
    <StrictMode>
      <KbEditorApp init={initData} />
    </StrictMode>
  );
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
