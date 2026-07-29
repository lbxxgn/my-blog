import { useCallback, useEffect, useRef, useState } from 'react';
import { autoSaveDoc, loadDraft } from '../lib/api';

export interface DraftData {
  title?: string;
  content: string;
  saved_at?: string;
  source: 'server' | 'local';
}

/** 新建文档（尚无服务端草稿）的本地暂存 key */
const LOCAL_DRAFT_KEY = 'kb-new-doc-draft';

interface UseAutoSaveOptions {
  docId?: number;
  autoSaveUrl?: string;
  draftUrl?: string;
  csrfToken: string;
  isNew?: boolean;
  getContent: () => Promise<{ title: string; content: string }>;
  debounceMs?: number;
}

export function useAutoSave({
  docId,
  autoSaveUrl,
  draftUrl,
  csrfToken,
  isNew = false,
  getContent,
  debounceMs = 3000,
}: UseAutoSaveOptions) {
  const [draftInfo, setDraftInfo] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftData | null>(null);
  const dirtyRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  const markDirty = useCallback(() => {
    dirtyRef.current = true;
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(() => {
      if (!dirtyRef.current) return;
      dirtyRef.current = false;
      getContent()
        .then(({ title, content }) => {
          if (!title.trim() && !content.trim()) return;
          if (docId && autoSaveUrl) {
            return autoSaveDoc(autoSaveUrl, csrfToken, { title, content })
              .then((data) => {
                setDraftInfo(`已自动保存 ${new Date(data.saved_at).toLocaleTimeString()}`);
              })
              .catch((err) => {
                console.error('Auto save failed:', err);
                setDraftInfo('自动保存失败，内容暂存于编辑器');
              });
          }
          if (isNew) {
            // 新建文档还没有 docId，无法走服务端草稿，先暂存 localStorage
            try {
              localStorage.setItem(
                LOCAL_DRAFT_KEY,
                JSON.stringify({ title, content, saved_at: new Date().toISOString() })
              );
              setDraftInfo(`已暂存到本地 ${new Date().toLocaleTimeString()}`);
            } catch (e) {
              console.warn('本地草稿暂存失败:', e);
            }
          }
        });
    }, debounceMs);
  }, [autoSaveUrl, csrfToken, debounceMs, docId, isNew, getContent]);

  // 加载可恢复的草稿：已有文档走服务端，新建文档读 localStorage
  useEffect(() => {
    if (docId && draftUrl) {
      loadDraft(draftUrl)
        .then((data) => {
          if (data.draft) {
            setDraft({ ...data.draft, source: 'server' });
          }
        })
        .catch(console.error);
      return;
    }
    if (isNew) {
      try {
        const raw = localStorage.getItem(LOCAL_DRAFT_KEY);
        if (raw) {
          const d = JSON.parse(raw);
          if (d && (d.content || d.title)) {
            setDraft({
              title: d.title,
              content: d.content || '',
              saved_at: d.saved_at,
              source: 'local',
            });
          }
        }
      } catch (e) {
        console.warn('读取本地草稿失败:', e);
      }
    }
  }, [docId, draftUrl, isNew]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  /** 关闭草稿横幅；本地草稿同时清掉，服务端草稿保留（下次保存会覆盖） */
  const dismissDraft = useCallback(() => {
    if (draft?.source === 'local') {
      try {
        localStorage.removeItem(LOCAL_DRAFT_KEY);
      } catch (e) {
        /* ignore */
      }
    }
    setDraft(null);
  }, [draft]);

  /** 保存成功后清理本地暂存 */
  const clearLocalDraft = useCallback(() => {
    try {
      localStorage.removeItem(LOCAL_DRAFT_KEY);
    } catch (e) {
      /* ignore */
    }
  }, []);

  return { draftInfo, draft, dismissDraft, clearLocalDraft, markDirty };
}
