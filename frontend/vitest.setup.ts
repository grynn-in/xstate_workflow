import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Mock ResizeObserver for React Flow
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
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

// Mock frappe global for tests
(global as Record<string, unknown>).frappe = {
  xcall: vi.fn(),
  call: vi.fn(),
  msgprint: vi.fn(),
  show_alert: vi.fn(),
};
