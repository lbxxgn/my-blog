import { useCallback, useEffect, useRef, useState } from 'react';
import { autoSaveDoc, loadDraft } from '../lib/api';

interface UseAutoSaveOptions {
  docId?: number;
  autoSaveUrl?: string;
  draftUrl?: string;
  csrfToken: string;
  getContent: () => Promise<{ title: string; content: string }>;
  debounceMs?: number;
}

export function useAutoSave({
  docId,
  autoSaveUrl,
  draftUrl,
  csrfToken,
  getContent,
  debounceMs = 3000,
}: UseAutoSaveOptions) {
  const [draftInfo, setDraftInfo] = useState<string | null>(null);
  const [hasDraft, setHasDraft] = useState(false);
  const dirtyRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  const markDirty = useCallback(() => {
    dirtyRef.current = true;
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(() => {
      if (!dirtyRef.current || !docId || !autoSaveUrl) return;
      dirtyRef.current = false;
      getContent()
        .then(({ title, content }) => {
          return autoSaveDoc(autoSaveUrl, csrfToken, { title, content });
        })
        .then((data) => {
          setDraftInfo(`已自动保存 ${new Date(data.saved_at).toLocaleTimeString()}`);
        })
        .catch((err) => {
          console.error('Auto save failed:', err);
        });
    }, debounceMs);
  }, [autoSaveUrl, csrfToken, debounceMs, docId, getContent]);

  useEffect(() => {
    if (!docId || !draftUrl) return;
    loadDraft(draftUrl)
      .then((data) => {
        if (data.draft) {
          setHasDraft(true);
          setDraftInfo(`存在 ${new Date(data.draft.saved_at).toLocaleString()} 的草稿`);
        }
      })
      .catch(console.error);
  }, [docId, draftUrl]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  return { draftInfo, hasDraft, markDirty };
}
