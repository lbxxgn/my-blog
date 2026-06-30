export interface Category {
  id: number;
  name: string;
  parent_id?: number | null;
  space?: string;
  slug?: string;
  sort_order?: number;
  icon?: string;
  description?: string;
  children?: Category[];
}

export interface KnowledgeDoc {
  id?: number;
  title: string;
  content: string;
  category_id?: number;
  is_published: boolean;
  sort_order: number;
  excerpt?: string;
  metadata?: Record<string, unknown>;
}

export interface Tag {
  id?: number;
  name: string;
}

export interface EditorInitData {
  doc?: KnowledgeDoc;
  tags?: Tag[];
  tree: Category[];
  treeFlattened: Array<{ id: number; name: string; indent: string }>;
  preselectCat?: number;
  csrfToken: string;
  saveUrl: string;
  previewUrl?: string;
  deleteUrl?: string;
  autoSaveUrl?: string;
  draftUrl?: string;
  uploadImageUrl: string;
  aiOrganizeUrl: string;
  aiSummaryUrl: string;
  aiContinueUrl: string;
  aiRecommendUrl: string;
  cardsUrl: string;
  isNew: boolean;
}

declare global {
  interface Window {
    __KB_EDITOR_INIT__?: EditorInitData;
  }
}
