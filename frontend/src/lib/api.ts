import { Category } from '../types';

export interface AiSuggestion {
  title?: string;
  summary?: string;
  tags?: string[];
  category?: Category;
  content_type?: string;
  source?: string;
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

/** 生成一个可读的设备标签（浏览器 + 系统），用于草稿冲突检测与展示。 */
export function getDeviceLabel(): string {
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  let browser = 'Browser';
  if (ua.includes('Edg')) browser = 'Edge';
  else if (ua.includes('Chrome')) browser = 'Chrome';
  else if (ua.includes('Firefox')) browser = 'Firefox';
  else if (ua.includes('Safari')) browser = 'Safari';
  let os = 'Unknown OS';
  if (ua.includes('Windows')) os = 'Windows';
  else if (ua.includes('Android')) os = 'Android';
  else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS';
  else if (ua.includes('Mac OS')) os = 'macOS';
  else if (ua.includes('Linux')) os = 'Linux';
  return `${browser} on ${os}`;
}

export interface AutoSaveResult {
  success: boolean;
  saved_at?: string;
  status?: 'saved' | 'conflict_detected';
  other_drafts?: ConflictDraft[];
  error?: string;
}

export interface ConflictDraft {
  id: number;
  title?: string;
  content?: string;
  device_info?: string;
  updated_at?: string;
}

export async function autoSaveDoc(
  url: string,
  csrfToken: string,
  payload: { title?: string; content: string; device_info?: string; content_format?: string }
): Promise<AutoSaveResult> {
  return postJson(url, payload, csrfToken);
}

export async function loadDraftById(draftId: number): Promise<ConflictDraft | null> {
  const res = await fetch(`/api/drafts/${draftId}`, { headers: { Accept: 'application/json' } });
  const data = await res.json().catch(() => ({}));
  return (data && data.draft) || null;
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
