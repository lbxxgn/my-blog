import { useCallback, useState } from 'react';
import { BlockNoteEditor } from '@blocknote/core';
import { Category } from '../types';
import {
  continueWriting,
  generateSummary,
  loadHistoryCards,
  organizeContent,
} from '../lib/api';

interface AiPanelProps {
  editor: BlockNoteEditor | null;
  title: string;
  csrfToken: string;
  aiOrganizeUrl: string;
  aiSummaryUrl: string;
  aiContinueUrl: string;
  aiRecommendUrl: string;
  cardsUrl: string;
  tree: Category[];
  onTitleChange: (title: string) => void;
  onTagsChange: (tags: string) => void;
  onCategoryChange: (categoryId: number | '') => void;
}

function flattenCategories(cats: Category[]): Category[] {
  return cats.reduce<Category[]>((acc, cat) => {
    acc.push(cat);
    if (cat.children) {
      acc.push(...flattenCategories(cat.children));
    }
    return acc;
  }, []);
}

export function AiPanel({
  editor,
  title,
  csrfToken,
  aiOrganizeUrl,
  aiSummaryUrl,
  aiContinueUrl,
  cardsUrl,
  tree,
  onTitleChange,
  onTagsChange,
  onCategoryChange,
}: AiPanelProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<any>(null);
  const [summary, setSummary] = useState('');
  const [cards, setCards] = useState<any[]>([]);
  const [cardQuery, setCardQuery] = useState('');
  const [status, setStatus] = useState('');

  const getMarkdown = useCallback(async () => {
    if (!editor) return '';
    return editor.blocksToMarkdownLossy(editor.document);
  }, [editor]);

  const handleOrganize = async () => {
    if (!editor) return;
    setLoading('organize');
    setStatus('正在整理内容...');
    try {
      const content = await getMarkdown();
      const categories = flattenCategories(tree).map((c) => ({
        id: c.id,
        name: c.name,
      }));
      const sug = await organizeContent(aiOrganizeUrl, csrfToken, {
        title,
        content,
        categories,
      });
      setSuggestion(sug);
      setStatus('整理建议已生成');
    } catch (e) {
      setStatus('整理失败：' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(null);
    }
  };

  const applySuggestion = () => {
    if (!suggestion) return;
    if (suggestion.title) onTitleChange(suggestion.title);
    if (suggestion.tags?.length) onTagsChange(suggestion.tags.join(', '));
    if (suggestion.category?.id) onCategoryChange(suggestion.category.id);
    setStatus('建议已应用');
  };

  const handleSummary = async () => {
    if (!editor) return;
    setLoading('summary');
    setStatus('正在生成摘要...');
    try {
      const content = await getMarkdown();
      const sum = await generateSummary(aiSummaryUrl, csrfToken, { title, content });
      setSummary(sum);
      setStatus('摘要已生成');
    } catch (e) {
      setStatus('摘要生成失败：' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(null);
    }
  };

  const insertSummary = async () => {
    if (!editor || !summary) return;
    const current = await getMarkdown();
    const newContent = `**摘要：**${summary}\n\n${current}`;
    const blocks = await editor.tryParseMarkdownToBlocks(newContent);
    editor.replaceBlocks(editor.document, blocks);
    setStatus('摘要已插入正文开头');
  };

  const handleContinue = async () => {
    if (!editor) return;
    setLoading('continue');
    setStatus('正在续写...');
    try {
      const content = await getMarkdown();
      const continuation = await continueWriting(aiContinueUrl, csrfToken, {
        title,
        content,
      });
      const blocks = await editor.tryParseMarkdownToBlocks(continuation);
      editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
      setStatus('续写内容已插入');
    } catch (e) {
      setStatus('续写失败：' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(null);
    }
  };

  const loadCards = async () => {
    setLoading('cards');
    try {
      const items = await loadHistoryCards(cardsUrl, cardQuery);
      setCards(items);
    } catch (e) {
      setStatus('加载历史卡片失败');
    } finally {
      setLoading(null);
    }
  };

  const insertCard = async (card: any, asReference: boolean) => {
    if (!editor) return;
    const text = card.content || '';
    const truncated = text.length > 220 ? text.slice(0, 220) + '...' : text;
    const md = asReference
      ? `> **延伸阅读：[${card.title || '未命名'}]**\n> ${truncated}\n\n`
      : `> **历史笔记：[${card.title || '未命名'}]**\n> ${truncated}\n\n`;
    const blocks = await editor.tryParseMarkdownToBlocks(md);
    editor.insertBlocks(blocks, editor.document[editor.document.length - 1].id);
    setStatus(`已插入「${card.title || '未命名'}」`);
  };

  if (!editor) {
    return <div className="kb-panel-empty">编辑器加载中...</div>;
  }

  return (
    <div className="kb-ai-panel">
      <h4>AI 辅助</h4>

      <div className="kb-ai-section">
        <button
          className="kb-ai-btn"
          onClick={handleOrganize}
          disabled={loading === 'organize'}
        >
          {loading === 'organize' ? '整理中...' : '整理内容'}
        </button>
        {suggestion && (
          <div className="kb-ai-suggestion">
            <p><strong>标题：</strong>{suggestion.title}</p>
            <p><strong>摘要：</strong>{suggestion.summary}</p>
            <p><strong>标签：</strong>{suggestion.tags?.join(', ')}</p>
            {suggestion.category && (
              <p><strong>目录：</strong>{suggestion.category.name}</p>
            )}
            <button className="kb-ai-btn kb-ai-btn-secondary" onClick={applySuggestion}>
              应用建议
            </button>
          </div>
        )}
      </div>

      <div className="kb-ai-section">
        <button
          className="kb-ai-btn"
          onClick={handleSummary}
          disabled={loading === 'summary'}
        >
          {loading === 'summary' ? '生成中...' : '生成摘要'}
        </button>
        {summary && (
          <div className="kb-ai-suggestion">
            <p>{summary}</p>
            <button className="kb-ai-btn kb-ai-btn-secondary" onClick={insertSummary}>
              插入摘要
            </button>
          </div>
        )}
      </div>

      <div className="kb-ai-section">
        <button
          className="kb-ai-btn"
          onClick={handleContinue}
          disabled={loading === 'continue'}
        >
          {loading === 'continue' ? '续写中...' : 'AI 续写'}
        </button>
      </div>

      <div className="kb-ai-section">
        <h5>历史卡片</h5>
        <div className="kb-ai-search">
          <input
            type="text"
            placeholder="搜索历史卡片..."
            value={cardQuery}
            onChange={(e) => setCardQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadCards()}
          />
          <button onClick={loadCards} disabled={loading === 'cards'}>
            {loading === 'cards' ? '加载中...' : '搜索'}
          </button>
        </div>
        <div className="kb-ai-cards">
          {cards.map((card) => (
            <div key={card.id} className="kb-ai-card-item">
              <div className="kb-ai-card-title">{card.title || '未命名'}</div>
              <div className="kb-ai-card-preview">
                {(card.content || '').slice(0, 80)}...
              </div>
              <div className="kb-ai-card-actions">
                <button onClick={() => insertCard(card, false)}>插入摘录</button>
                <button onClick={() => insertCard(card, true)}>插入引用</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {status && <div className="kb-ai-status">{status}</div>}
    </div>
  );
}
