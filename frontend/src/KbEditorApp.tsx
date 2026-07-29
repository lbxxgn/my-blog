import { useCallback, useEffect, useRef, useState } from 'react';
import { BlockNoteEditor } from '@blocknote/core';
import { flushSync } from 'react-dom';
import { KbBlockNoteEditor } from './components/KbBlockNoteEditor';
import { AiPanel } from './components/AiPanel';
import { TocPanel } from './components/TocPanel';
import { MetaPanel } from './components/MetaPanel';
import { useAutoSave } from './hooks/useAutoSave';
import { EditorInitData } from './types';

interface KbEditorAppProps {
  init: EditorInitData;
}

export function KbEditorApp({ init }: KbEditorAppProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const contentFieldRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(init.doc?.title || '');
  const [categoryId, setCategoryId] = useState<number | ''>(
    init.doc?.category_id || init.preselectCat || ''
  );
  const [tags, setTags] = useState(
    init.tags?.map((t) => t.name).join(', ') || ''
  );
  const [sortOrder, setSortOrder] = useState(init.doc?.sort_order ?? 0);
  const [isPublished, setIsPublished] = useState(
    init.isNew ? false : (init.doc?.is_published ?? false)
  );
  const [editorInstance, setEditorInstance] = useState<BlockNoteEditor | null>(null);
  const editorRef = useRef<BlockNoteEditor | null>(null);
  const [activePanel, setActivePanel] = useState<'ai' | 'toc' | 'meta' | null>('toc');
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [statusMessage, setStatusMessage] = useState('未修改');
  // 新建文档首次保存后切换为"编辑已有文档"，避免重复创建
  const [isNewDoc, setIsNewDoc] = useState(init.isNew);
  const [docId, setDocId] = useState<number | undefined>(init.doc?.id);
  const [saveUrl, setSaveUrl] = useState(init.saveUrl);
  const [autoSaveUrl, setAutoSaveUrl] = useState(init.autoSaveUrl);
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(false);
  const navigatingRef = useRef(false);

  const { draftInfo, draft, dismissDraft, clearLocalDraft, markDirty } = useAutoSave({
    docId,
    autoSaveUrl,
    draftUrl: init.draftUrl,
    csrfToken: init.csrfToken,
    isNew: isNewDoc,
    getContent: async () => {
      if (!editorInstance) return { title, content: '' };
      const md = await editorInstance.blocksToMarkdownLossy(editorInstance.document);
      return { title, content: md };
    },
  });

  const handleDirty = useCallback(() => {
    markDirty();
    setDirty(true);
  }, [markDirty]);

  const handleEditorChange = useCallback(() => {
    handleDirty();
    setSaveStatus('idle');
    setStatusMessage('有未保存修改');
  }, [handleDirty]);

  const handleSave = useCallback(async (stay: boolean) => {
    const editor = editorRef.current;
    if (!editor || !formRef.current || !contentFieldRef.current) {
      setSaveStatus('error');
      setStatusMessage(
        '保存未就绪：' +
          (!editorInstance ? '编辑器实例缺失 ' : '') +
          (!formRef.current ? '表单引用缺失 ' : '') +
          (!contentFieldRef.current ? '内容字段缺失' : '')
      );
      return;
    }
    if (!title.trim()) {
      setSaveStatus('error');
      setStatusMessage('请填写标题');
      document.getElementById('kb-title')?.focus();
      return;
    }
    if (!categoryId) {
      setSaveStatus('error');
      setStatusMessage('请选择目录');
      document.getElementById('kb-category')?.focus();
      return;
    }
    setIsSaving(true);
    setSaveStatus('saving');
    setStatusMessage('正在保存...');
    try {
      const markdown = await editor.blocksToMarkdownLossy(editor.document);
      contentFieldRef.current.value = markdown;
      const res = await fetch(saveUrl, {
        method: 'POST',
        body: new FormData(formRef.current),
        headers: {
          'X-CSRFToken': init.csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
      });
      const data = await res.json().catch(() => ({} as Record<string, unknown>));
      if (!res.ok || !data.success) {
        throw new Error(
          (data.error as string) ||
            (res.status === 401 ? '登录已过期，请重新登录' : `保存失败 (${res.status})`)
        );
      }
      setSaveStatus('saved');
      setStatusMessage(`已保存 ${new Date().toLocaleTimeString()}`);
      setDirty(false);
      clearLocalDraft();
      // 新建文档首次保存：切换为编辑模式，后续保存走 edit 路由
      if (isNewDoc && data.doc_id) {
        setIsNewDoc(false);
        setDocId(data.doc_id as number);
        if (data.edit_url) setSaveUrl(data.edit_url as string);
        if (data.autosave_url) setAutoSaveUrl(data.autosave_url as string);
        if (data.edit_url) window.history.replaceState(null, '', data.edit_url as string);
      }
      if (!stay) {
        navigatingRef.current = true;
        window.location.href = (data.redirect as string) || window.location.href;
        return;
      }
    } catch (e) {
      setSaveStatus('error');
      setStatusMessage('保存失败：' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setIsSaving(false);
    }
  }, [editorInstance, title, categoryId, saveUrl, isNewDoc, init.csrfToken, clearLocalDraft]);

  // 发布 / 取消发布：切换状态后保存并留在编辑器
  const handlePublishToggle = useCallback(async () => {
    if (isSaving || !editorInstance) return;
    // Ensure the hidden is_published input is rendered before submitting.
    flushSync(() => setIsPublished(!isPublished));
    await handleSave(true);
  }, [handleSave, isPublished, isSaving, editorInstance]);

  // 恢复草稿：回填标题和正文
  const handleRestoreDraft = useCallback(async () => {
    if (!draft) return;
    if (draft.title) {
      setTitle(draft.title);
    }
    const editor = editorRef.current;
    if (editor && draft.content) {
      try {
        const blocks = await editor.tryParseMarkdownToBlocks(draft.content);
        editor.replaceBlocks(editor.document, blocks);
      } catch (e) {
        console.error('恢复草稿失败:', e);
      }
    }
    handleDirty();
    dismissDraft();
  }, [draft, handleDirty, dismissDraft]);

  // Expose save handler for automated end-to-end tests.
  useEffect(() => {
    editorRef.current = editorInstance;
  }, [editorInstance]);
  useEffect(() => {
    (window as any).__KB_SAVE__ = () => handleSave(true);
  }, [handleSave]);

  // 未保存修改时离开页面前提醒
  useEffect(() => {
    dirtyRef.current = dirty;
  }, [dirty]);
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirtyRef.current && !navigatingRef.current) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, []);

  const saveButtonLabel = isSaving
    ? '保存中...'
    : editorInstance
    ? '保存'
    : '编辑器加载中...';

  return (
    <div className="kb-editor-layout">
      <main className="kb-editor-main">
        {draft && (
          <div className="kb-draft-banner">
            <span>
              检测到{draft.saved_at ? ` ${new Date(draft.saved_at).toLocaleString()} ` : ''}的
              {draft.source === 'local' ? '本地' : ''}草稿
            </span>
            <button type="button" className="btn btn-primary" onClick={handleRestoreDraft}>
              恢复草稿
            </button>
            <button type="button" className="btn" onClick={dismissDraft}>
              忽略
            </button>
          </div>
        )}
        <form
          ref={formRef}
          method="POST"
          action={saveUrl}
          className="kb-editor-form"
          onSubmit={(e) => e.preventDefault()}
        >
          <input type="hidden" name="csrf_token" value={init.csrfToken} />
          <input type="hidden" name="content" ref={contentFieldRef} />
          {isPublished && <input type="hidden" name="is_published" value="1" />}

          <div className="kb-form-row">
            <div className="kb-form-group kb-form-group-wide">
              <label htmlFor="kb-title">标题</label>
              <input
                id="kb-title"
                name="title"
                type="text"
                required
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  handleDirty();
                }}
                placeholder="输入文档标题"
              />
            </div>
          </div>

          <div className="kb-form-row kb-form-row-3">
            <div className="kb-form-group">
              <label htmlFor="kb-category">目录</label>
              <select
                id="kb-category"
                name="category_id"
                required
                value={categoryId}
                onChange={(e) => {
                  setCategoryId(e.target.value ? Number(e.target.value) : '');
                  handleDirty();
                }}
              >
                <option value="">请选择目录</option>
                {init.treeFlattened.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.indent}{cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="kb-form-group">
              <label htmlFor="kb-tags">标签（逗号分隔）</label>
              <input
                id="kb-tags"
                name="tags"
                type="text"
                value={tags}
                onChange={(e) => {
                  setTags(e.target.value);
                  handleDirty();
                }}
              />
            </div>
            <div className="kb-form-group kb-form-group-narrow">
              <label htmlFor="kb-sort">排序</label>
              <input
                id="kb-sort"
                name="sort_order"
                type="number"
                min={0}
                value={sortOrder}
                onChange={(e) => {
                  setSortOrder(Number(e.target.value));
                  handleDirty();
                }}
              />
            </div>
          </div>
        </form>

        <div className="kb-editor-canvas">
          <KbBlockNoteEditor
            initialMarkdown={init.doc?.content || ''}
            uploadImageUrl={init.uploadImageUrl}
            csrfToken={init.csrfToken}
            onChange={(editor) => {
              setEditorInstance(editor);
              handleEditorChange();
            }}
          />
        </div>

        <div className="kb-editor-footer-actions">
          <div className="kb-save-status">
            <span className={`kb-status-dot kb-status-${saveStatus}`} />
            <span>{statusMessage}</span>
            {draftInfo && <span className="kb-draft-hint">草稿：{draftInfo}</span>}
          </div>
          <div className="kb-editor-actions">
            {!init.isNew && init.previewUrl && (
              <a href={init.previewUrl} className="btn" target="_blank" rel="noreferrer">
                预览
              </a>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handlePublishToggle}
              disabled={isSaving || !editorInstance}
            >
              {isPublished ? '取消发布' : '发布'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleSave(false)}
              disabled={isSaving || !editorInstance}
            >
              保存并查看
            </button>
            <button
              type="button"
              data-testid="kb-save-btn"
              className="btn btn-primary"
              onClick={() => handleSave(true)}
              disabled={isSaving || !editorInstance}
            >
              {saveButtonLabel}
            </button>
          </div>
        </div>
      </main>

      <div className="kb-editor-right">
        <aside className="kb-editor-sidebar">
          <div className="kb-panel-tabs">
            <button
              className={activePanel === 'toc' ? 'active' : ''}
              onClick={() => setActivePanel('toc')}
            >
              大纲
            </button>
            <button
              className={activePanel === 'ai' ? 'active' : ''}
              onClick={() => setActivePanel('ai')}
            >
              AI
            </button>
            <button
              className={activePanel === 'meta' ? 'active' : ''}
              onClick={() => setActivePanel('meta')}
            >
              信息
            </button>
          </div>
          <div className="kb-panel-content">
            {activePanel === 'toc' && <TocPanel editor={editorInstance} />}
            {activePanel === 'ai' && (
              <AiPanel
                editor={editorInstance}
                title={title}
                csrfToken={init.csrfToken}
                aiOrganizeUrl={init.aiOrganizeUrl}
                aiSummaryUrl={init.aiSummaryUrl}
                aiContinueUrl={init.aiContinueUrl}
                aiRecommendUrl={init.aiRecommendUrl}
                cardsUrl={init.cardsUrl}
                tree={init.tree}
                onTitleChange={setTitle}
                onTagsChange={setTags}
                onCategoryChange={setCategoryId}
              />
            )}
            {activePanel === 'meta' && (
              <MetaPanel
                title={title}
                tags={tags}
                categoryId={categoryId}
                treeFlattened={init.treeFlattened}
                isPublished={isPublished}
                doc={init.doc}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
