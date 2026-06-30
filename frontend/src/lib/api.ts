import { Category } from '../types';

export interface AiSuggestion {
  title?: string;
  summary?: string;
  tags?: string[];
  category?: Category;
  content_type?: string;
  source?: string;
}

export interface Card {
  id: number;
  title?: string;
  content?: string;
  status?: string;
  created_at?: string;
  tags?: string[];
}

async function postJson(url: string, body: object, csrfToken: string) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      'Accept': 'application/json',
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.success) {
    throw new Error(data.error || `请求失败 (${res.status})`);
  }
  return data;
}

export async function autoSaveDoc(
  url: string,
  csrfToken: string,
  payload: { title?: string; content: string }
) {
  return postJson(url, payload, csrfToken);
}

export async function loadDraft(url: string): Promise<{
  success: boolean;
  draft?: { title?: string; content: string; saved_at: string } | null;
}> {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  return res.json().catch(() => ({ success: false, draft: null }));
}

export async function uploadImage(
  url: string,
  csrfToken: string,
  file: File
): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: formData,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.success || !data.url) {
    throw new Error(data.error || '图片上传失败');
  }
  return data.url;
}

export async function organizeContent(
  url: string,
  csrfToken: string,
  payload: { title?: string; content: string; categories: Category[] }
): Promise<AiSuggestion> {
  const data = await postJson(url, payload, csrfToken);
  return data.suggestion || {};
}

export async function generateSummary(
  url: string,
  csrfToken: string,
  payload: { title?: string; content: string }
): Promise<string> {
  const data = await postJson(url, payload, csrfToken);
  return data.summary || '';
}

export async function continueWriting(
  url: string,
  csrfToken: string,
  payload: { title?: string; content: string }
): Promise<string> {
  const data = await postJson(url, payload, csrfToken);
  return data.content || '';
}

export async function loadHistoryCards(
  url: string,
  query: string = '',
  limit: number = 20
): Promise<Card[]> {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  params.set('limit', String(limit));
  const res = await fetch(`${url}?${params.toString()}`, {
    headers: { Accept: 'application/json' },
  });
  const data = await res.json().catch(() => ({}));
  return data.cards || [];
}
