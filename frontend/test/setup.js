import { afterEach, vi } from 'vitest';

vi.stubGlobal('ResizeObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

Object.defineProperty(URL, 'createObjectURL', {
  writable: true,
  value: vi.fn(() => 'blob:test'),
});

Object.defineProperty(window, 'open', {
  writable: true,
  value: vi.fn(),
});

afterEach(() => {
  document.body.innerHTML = '';
  document.head.innerHTML = '';
  vi.clearAllMocks();
});
