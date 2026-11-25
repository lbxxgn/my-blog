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

export interface AiStatus {
  ai_enabled: boolean;
  ai_configured: boolean;
}

/** 读取后台 AI 功能开关与模型配置状态。 */
export async function fetchAiStatus(url = '/admin/ai/status'): Promise<AiStatus> {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  const data = await res.json().catch(() => ({}));
  return {
    ai_enabled: Boolean(data.ai_enabled),
    ai_configured: Boolean(data.ai_configured),
  };
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

/** 每个标签页一个稳定 token，用于区分同设备多标签的草稿。 */
export function getDeviceToken(): string {
  try {
    let token = sessionStorage.getItem('kb_draft_device_token');
    if (!token) {
      token = (crypto && typeof crypto.randomUUID === 'function')
        ? crypto.randomUUID()
        : `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      sessionStorage.setItem('kb_draft_device_token', token);
    }
    return token;
  } catch {
    return `tab-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
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
  payload: { title?: string; content: string; device_info?: string; device_token?: string; content_format?: string }
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

export interface SaveDocResult {
  success: boolean;
  doc_id?: number;
  edit_url?: string;
  autosave_url?: string;
  redirect?: string;
  error?: string;
}

/** 提交知识库文档表单（含标题、目录、正文等），失败时抛出可直接展示的错误。 */
export async function saveDoc(
  url: string,
  csrfToken: string,
  formData: FormData
): Promise<SaveDocResult> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest',
      Accept: 'application/json',
    },
    body: formData,
  });
  const data = (await res.json().catch(() => ({}))) as SaveDocResult;
  if (!res.ok || !data.success) {
    throw new Error(
      data.error ||
        (res.status === 401 ? '登录已过期，请重新登录' : `保存失败 (${res.status})`)
    );
  }
  return data;
}

export interface RelatedItem {
  source_type: string;
  source_id: number;
  title: string;
  excerpt: string;
  url: string | null;
  score: number;
}

export interface RelatedResponse {
  ok: boolean;
  status: number;
  data: { items?: RelatedItem[]; error?: string };
}

/** 请求相关内容推荐；保留 HTTP 状态码，便于区分“未配置 embedding”等情况。 */
export async function requestRelated(
  url: string,
  csrfToken: string,
  payload: { text: string; exclude_type?: string; exclude_id?: number; limit?: number }
): Promise<RelatedResponse> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });
  const data = (await res.json().catch(() => ({}))) as RelatedResponse['data'];
  return { ok: res.ok, status: res.status, data };
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
  return data.continuation || '';
}
