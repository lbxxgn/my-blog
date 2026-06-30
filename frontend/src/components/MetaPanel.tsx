import { KnowledgeDoc } from '../types';

interface MetaPanelProps {
  title: string;
  tags: string;
  categoryId: number | '';
  treeFlattened: Array<{ id: number; name: string; indent: string }>;
  isPublished: boolean;
  doc?: KnowledgeDoc;
}

export function MetaPanel({
  tags,
  categoryId,
  treeFlattened,
  isPublished,
  doc,
}: MetaPanelProps) {
  const categoryName = treeFlattened.find((c) => c.id === categoryId)?.name || '未选择';

  return (
    <div className="kb-meta-panel">
      <h4>文档信息</h4>
      <dl>
        <dt>状态</dt>
        <dd>{isPublished ? '已发布' : '草稿'}</dd>
        <dt>目录</dt>
        <dd>{categoryName}</dd>
        {tags && (
          <>
            <dt>标签</dt>
            <dd>{tags}</dd>
          </>
        )}
        {doc?.id && (
          <>
            <dt>文档 ID</dt>
            <dd>{doc.id}</dd>
          </>
        )}
      </dl>
    </div>
  );
}
