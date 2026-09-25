import { useEffect, useRef, useState } from 'react';
import { BlockNoteEditor } from '@blocknote/core';

interface RelatedPanelProps {
  editor: BlockNoteEditor | null;
  csrfToken: string;
  relatedUrl: string;
  excludeId?: number;
}

interface RelatedItem {
  source_type: string;
  source_id: number;
  title: string;
  excerpt: string;
  url: string | null;
  score: number;
}

type PanelState =
  | { kind: 'idle' }
  | { kind: 'too_short' }
  | { kind: 'not_configured' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'done'; items: RelatedItem[] };

const MIN_TEXT_LENGTH = 200;
const DEBOUNCE_MS = 2000;

function extractPlainText(editor: BlockNoteEditor): string {
  const parts: string[] = [];
  const walk = (blocks: any[]) => {
    blocks.forEach((block) => {
      if (Array.isArray(block.content)) {
        block.content.forEach((c: any) => {
          if (typeof c === 'string') parts.push(c);
          else if (c && typeof c.text === 'string') parts.push(c.text);
        });
      }
      if (Array.isArray(block.children) && block.children.length) {
        walk(block.children);
      }
    });
  };
  walk(editor.document as any[]);
  return parts.join(' ').replace(/\s+/g, ' ').trim();
}

export function RelatedPanel({ editor, csrfToken, relatedUrl, excludeId }: RelatedPanelProps) {
  const [state, setState] = useState<PanelState>({ kind: 'idle' });
  const timerRef = useRef<number | null>(null);
  const seqRef = useRef(0);

  useEffect(() => {
    if (!editor) return;

    const requestRelated = async (text: string) => {
      const seq = ++seqRef.current;
      setState({ kind: 'loading' });
      try {
        const res = await fetch(relatedUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            Accept: 'application/json',
          },
          body: JSON.stringify({
            text,
            exclude_type: 'doc',
            exclude_id: excludeId,
            limit: 8,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (seq !== seqRef.current) return;
        if (res.status === 400 && data.error === 'embedding_not_configured') {
          setState({ kind: 'not_configured' });
          return;
        }
        if (!res.ok) {
          setState({ kind: 'error', message: data.error || `请求失败 (${res.status})` });
          return;
        }
        setState({ kind: 'done', items: data.items || [] });
      } catch (e) {
        if (seq !== seqRef.current) return;
        setState({ kind: 'error', message: e instanceof Error ? e.message : String(e) });
      }
    };

    const onChange = () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => {
        const text = extractPlainText(editor);
        if (text.length < MIN_TEXT_LENGTH) {
          setState({ kind: 'too_short' });
          return;
        }
        requestRelated(text);
      }, DEBOUNCE_MS);
    };

    const unsub = editor.onChange(onChange);
    return () => {
      unsub();
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [editor, csrfToken, relatedUrl, excludeId]);

  if (!editor) {
    return <div className="kb-panel-empty">编辑器加载中...</div>;
  }

  return (
    <div className="kb-related-panel">
      <h4>相关内容</h4>
      <p className="kb-related-hint">写作时自动推荐相关的文章、卡片和文档。</p>
      {state.kind === 'idle' && (
        <div className="kb-panel-empty">开始写作后自动检索相关内容。</div>
      )}
      {state.kind === 'too_short' && (
        <div className="kb-panel-empty">再多写一点（{MIN_TEXT_LENGTH} 字以上）就会自动推荐相关内容。</div>
      )}
      {state.kind === 'not_configured' && (
        <div className="kb-panel-empty">
          相关推荐需要配置 Embedding 模型，
          <a href="/admin/ai" target="_blank" rel="noreferrer">
            前往 AI 设置
          </a>
          。
        </div>
      )}
      {state.kind === 'loading' && <div className="kb-panel-empty">检索中...</div>}
      {state.kind === 'error' && <div className="kb-panel-empty">出错了：{state.message}</div>}
      {state.kind === 'done' && state.items.length === 0 && (
        <div className="kb-panel-empty">没有找到相关内容。</div>
      )}
      {state.kind === 'done' && state.items.length > 0 && (
        <ul className="kb-related-list">
          {state.items.map((item) => (
            <li key={`${item.source_type}-${item.source_id}`} className="kb-related-item">
              <div className="kb-related-item-head">
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                ) : (
                  <span>{item.title}</span>
                )}
                <span className="kb-related-score">{Math.round(item.score * 100)}%</span>
              </div>
              {item.excerpt && <p className="kb-related-excerpt">{item.excerpt}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
