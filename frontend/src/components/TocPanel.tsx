import { useEffect, useState } from 'react';
import { BlockNoteEditor } from '@blocknote/core';

interface TocPanelProps {
  editor: BlockNoteEditor | null;
}

interface TocItem {
  id: string;
  text: string;
  level: number;
}

export function TocPanel({ editor }: TocPanelProps) {
  const [items, setItems] = useState<TocItem[]>([]);

  useEffect(() => {
    if (!editor) return;
    const update = () => {
      const headings: TocItem[] = [];
      editor.document.forEach((block) => {
        if (block.type === 'heading') {
          const content = Array.isArray(block.content)
            ? block.content.map((c: any) => (typeof c === 'string' ? c : c.text || '')).join('')
            : '';
          headings.push({
            id: block.id,
            text: content || '无标题',
            level: block.props?.level || 1,
          });
        }
      });
      setItems(headings);
    };
    update();
    const unsub = editor.onChange(update);
    return () => {
      unsub();
    };
  }, [editor]);

  if (!editor) {
    return <div className="kb-panel-empty">编辑器加载中...</div>;
  }

  if (items.length === 0) {
    return <div className="kb-panel-empty">暂无目录，添加标题后自动生成</div>;
  }

  return (
    <nav className="kb-toc-panel">
      <h4>文档大纲</h4>
      <ul>
        {items.map((item) => (
          <li key={item.id} className={`kb-toc-level-${item.level}`}>
            <a
              href={`#${item.id}`}
              onClick={(e) => {
                e.preventDefault();
                editor.setSelection(item.id, 'end');
              }}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
