import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAutoSave } from './useAutoSave';

const LOCAL_DRAFT_KEY = 'kb-new-doc-draft';

function mockFetchOnce(body: unknown, ok = true) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

/** 推进假定时器，同时把期间产生的微任务（fetch 链）跑完 */
async function tick(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe('useAutoSave', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('新建文档写本地暂存，不请求服务端', async () => {
    const fetchMock = mockFetchOnce({ success: true });
    const getContent = () => Promise.resolve({ title: '草稿标题', content: '正文' });

    const { result } = renderHook(() =>
      useAutoSave({ isNew: true, csrfToken: 'csrf', getContent, debounceMs: 1000 })
    );

    act(() => result.current.markDirty());
    await tick(1000);

    expect(result.current.draftInfo || '').toContain('已暂存到本地');
    const stored = JSON.parse(localStorage.getItem(LOCAL_DRAFT_KEY) || '{}');
    expect(stored.content).toBe('正文');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('已有文档防抖后调用自动保存接口并上报设备信息', async () => {
    const fetchMock = mockFetchOnce({ success: true, status: 'saved', saved_at: '2026-01-01T00:00:00Z' });
    const getContent = () => Promise.resolve({ title: '标题', content: '正文内容' });

    const { result } = renderHook(() =>
      useAutoSave({
        docId: 7,
        autoSaveUrl: '/api/knowledge/docs/7/autosave',
        draftUrl: '/api/knowledge/docs/7/draft',
        csrfToken: 'csrf-token',
        getContent,
        debounceMs: 1000,
      })
    );

    act(() => result.current.markDirty());
    // 防抖期内多次触发只应发一次请求
    act(() => result.current.markDirty());
    await tick(1000);

    // 挂载时还会请求一次草稿，这里只统计自动保存请求
    const saveCalls = fetchMock.mock.calls.filter(
      ([url]) => url === '/api/knowledge/docs/7/autosave'
    );
    expect(saveCalls).toHaveLength(1);
    const [url, init] = saveCalls[0];
    expect(url).toBe('/api/knowledge/docs/7/autosave');
    expect(init.method).toBe('POST');
    expect(init.headers['X-CSRFToken']).toBe('csrf-token');
    const payload = JSON.parse(init.body);
    expect(payload.content).toBe('正文内容');
    expect(payload.device_token).toBeTruthy();
    expect(payload.device_info).toContain('on');
    expect(result.current.draftInfo || '').toContain('已自动保存');
  });

  it('服务端返回冲突时暴露 conflict，供 UI 提示', async () => {
    mockFetchOnce({
      success: true,
      status: 'conflict_detected',
      other_drafts: [{ id: 3, content: '其他设备的草稿', device_info: 'Chrome on Windows' }],
    });
    const getContent = () => Promise.resolve({ title: '标题', content: '正文' });

    const { result } = renderHook(() =>
      useAutoSave({
        docId: 9,
        autoSaveUrl: '/api/auto',
        csrfToken: 'csrf',
        getContent,
        debounceMs: 500,
      })
    );

    act(() => result.current.markDirty());
    await tick(500);

    expect(result.current.conflict?.id).toBe(3);
    expect(result.current.draftInfo || '').toContain('其他设备');
  });

  it('保存失败时回退到本地备份', async () => {
    mockFetchOnce({ success: false, error: 'boom' }, false);
    const getContent = () => Promise.resolve({ title: '标题', content: '正文' });
    vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() =>
      useAutoSave({
        docId: 11,
        autoSaveUrl: '/api/auto',
        csrfToken: 'csrf',
        getContent,
        debounceMs: 500,
      })
    );

    act(() => result.current.markDirty());
    await tick(500);

    expect(result.current.draftInfo || '').toContain('自动保存失败');
    const backup = JSON.parse(localStorage.getItem('kb-doc-backup-11') || '{}');
    expect(backup.content).toBe('正文');
  });
});
