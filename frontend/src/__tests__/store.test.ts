import { describe, it, expect, beforeEach } from 'vitest';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

describe('localStorage mock', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('should store and retrieve values', () => {
    localStorageMock.setItem('dark_mode', 'true');
    expect(localStorageMock.getItem('dark_mode')).toBe('true');
  });

  it('should return null for missing keys', () => {
    expect(localStorageMock.getItem('nonexistent')).toBeNull();
  });
});

describe('Type definitions', () => {
  it('should have proper ApiResponse structure', () => {
    interface ApiResponse<T> {
      code: number;
      message: string;
      data: T;
    }
    const response: ApiResponse<{ test: number }> = {
      code: 0,
      message: 'ok',
      data: { test: 1 },
    };
    expect(response.code).toBe(0);
    expect(response.data.test).toBe(1);
  });
});
