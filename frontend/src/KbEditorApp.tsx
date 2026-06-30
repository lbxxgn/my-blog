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

  const { draftInfo, markDirty } = useAutoSave({
    docId: init.doc?.id,
    autoSaveUrl: init.autoSaveUrl,
    draftUrl: init.draftUrl,
    csrfToken: init.csrfToken,
    getContent: async () => {
      if (!editorInstance) return { title, content: '' };
      const md = await editorInstance.blocksToMarkdownLossy(editorInstance.document);
      return { title, content: md };
    },
  });

  const handleEditorChange = useCallback(() => {
    markDirty();
    setSaveStatus('idle');
    setStatusMessage('有未保存修改');
  }, [markDirty]);

  const handleSave = useCallback(async () => {
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
      formRef.current.submit();
    } catch (e) {
      setIsSaving(false);
      setSaveStatus('error');
      setStatusMessage('保存失败：' + (e instanceof Error ? e.message : String(e)));
    }
  }, [editorInstance, title, categoryId]);

  const handlePublish = useCallback(async () => {
    if (isSaving || !editorInstance || isPublished) return;
    // Ensure the hidden is_published input is rendered before submitting.
    flushSync(() => setIsPublished(true));
    await handleSave();
  }, [handleSave, isPublished, isSaving, editorInstance]);

  // Expose save handler for automated end-to-end tests.
  useEffect(() => {
    editorRef.current = editorInstance;
  }, [editorInstance]);
  useEffect(() => {
    (window as any).__KB_SAVE__ = handleSave;
  }, [handleSave]);

  const saveButtonLabel = isSaving
    ? '保存中...'
    : editorInstance
    ? '保存'
    : '编辑器加载中...';

  return (
    <div className="kb-editor-layout">
      <main className="kb-editor-main">
        <form
          ref={formRef}
          method="POST"
          action={init.saveUrl}
          className="kb-editor-form"
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
                  markDirty();
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
                  markDirty();
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
                  markDirty();
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
                  markDirty();
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
              onClick={handlePublish}
              disabled={isSaving || !editorInstance || isPublished}
            >
              {isPublished ? '已发布' : '发布'}
            </button>
            <button
              type="button"
              data-testid="kb-save-btn"
              className="btn btn-primary"
              onClick={handleSave}
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
