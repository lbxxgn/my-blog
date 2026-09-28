import { useCallback, useState } from 'react';
import { BlockNoteEditor } from '@blocknote/core';
import { Category } from '../types';
import {
  continueWriting,
  generateSummary,
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
  tree,
  onTitleChange,
  onTagsChange,
  onCategoryChange,
}: AiPanelProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<any>(null);
  const [summary, setSummary] = useState('');
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

      {status && <div className="kb-ai-status">{status}</div>}
    </div>
  );
}
