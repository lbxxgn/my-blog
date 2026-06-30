import { useEffect, useRef, useState } from 'react';
import { BlockNoteEditor } from '@blocknote/core';
import { useCreateBlockNote } from '@blocknote/react';
import { BlockNoteView } from '@blocknote/mantine';
import '@blocknote/core/fonts/inter.css';
import '@blocknote/mantine/style.css';
import { uploadImage } from '../lib/api';

interface KbBlockNoteEditorProps {
  initialMarkdown: string;
  uploadImageUrl: string;
  csrfToken: string;
  onChange?: (editor: BlockNoteEditor) => void;
}

export function KbBlockNoteEditor({
  initialMarkdown,
  uploadImageUrl,
  csrfToken,
  onChange,
}: KbBlockNoteEditorProps) {
  const [isReady, setIsReady] = useState(false);
  const initialMarkdownRef = useRef(initialMarkdown);

  const editor = useCreateBlockNote({
    uploadFile: async (file: File) => {
      const url = await uploadImage(uploadImageUrl, csrfToken, file);
      return url;
    },
  });

  // Parse initial Markdown and replace editor contents once the editor is ready.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const blocks = await editor.tryParseMarkdownToBlocks(
        initialMarkdownRef.current || ''
      );
      if (cancelled) return;
      editor.replaceBlocks(editor.document, blocks);
      // Expose the editor instance for testing / debugging.
      (window as any).__KB_EDITOR_INSTANCE__ = editor;
      setIsReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [editor]);

  // Subscribe to editor content changes after initial content is loaded.
  useEffect(() => {
    if (!isReady) return;
    // Notify parent that the editor instance is ready.
    onChange?.(editor);
    const unsub = editor.onChange(() => {
      onChange?.(editor);
    });
    return () => {
      unsub();
    };
  }, [editor, isReady, onChange]);

  if (!isReady) {
    return <div className="kb-editor-loading">正在加载编辑器...</div>;
  }

  return (
    <div className="kb-blocknote-wrapper">
      <BlockNoteView editor={editor} />
    </div>
  );
}
