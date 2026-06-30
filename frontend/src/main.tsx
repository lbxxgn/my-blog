import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { KbEditorApp } from './KbEditorApp';
import { EditorInitData } from './types';
import './styles/kb-editor.css';

function init() {
  const container = document.getElementById('kb-editor-root');
  if (!container) {
    console.error('kb-editor-root not found');
    return;
  }

  const initData = (window.__KB_EDITOR_INIT__ || {}) as EditorInitData;
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
