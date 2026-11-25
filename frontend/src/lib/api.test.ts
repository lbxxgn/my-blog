import { describe, expect, it, beforeEach } from 'vitest';
import { getDeviceLabel, getDeviceToken } from './api';

function setUserAgent(ua: string) {
  Object.defineProperty(window.navigator, 'userAgent', {
    value: ua,
    configurable: true,
  });
}

const UA = {
  chromeMac:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  edgeWindows:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
  firefoxLinux:
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
  safariIPhone:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  unknown: 'curl/8.4.0',
};

describe('getDeviceLabel', () => {
  beforeEach(() => setUserAgent(UA.chromeMac));

  it('识别 Chrome + macOS', () => {
    expect(getDeviceLabel()).toBe('Chrome on macOS');
  });

  it('识别 Edge + Windows', () => {
    setUserAgent(UA.edgeWindows);
    expect(getDeviceLabel()).toBe('Edge on Windows');
  });

  it('识别 Firefox + Linux', () => {
    setUserAgent(UA.firefoxLinux);
    expect(getDeviceLabel()).toBe('Firefox on Linux');
  });

  it('识别 iOS Safari', () => {
    setUserAgent(UA.safariIPhone);
    expect(getDeviceLabel()).toBe('Safari on iOS');
  });

  it('无法识别时给出兜底文案', () => {
    setUserAgent(UA.unknown);
    expect(getDeviceLabel()).toBe('Browser on Unknown OS');
  });
});

describe('getDeviceToken', () => {
  beforeEach(() => sessionStorage.clear());

  it('同一会话内保持稳定', () => {
    const first = getDeviceToken();
    expect(first).toBeTruthy();
    expect(getDeviceToken()).toBe(first);
    expect(sessionStorage.getItem('kb_draft_device_token')).toBe(first);
  });

  it('不同会话（清空 sessionStorage）会生成新 token', () => {
    const first = getDeviceToken();
    sessionStorage.clear();
    expect(getDeviceToken()).not.toBe(first);
  });
});
