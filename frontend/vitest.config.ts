import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['packages/**/*.test.{ts,tsx}', 'apps/**/*.test.{ts,tsx}'],
    exclude: ['**/node_modules/**', '**/dist/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['packages/*/src/**/*.{ts,tsx}'],
      exclude: [
        '**/node_modules/**',
        '**/index.ts',
        '**/*.d.ts',
        '**/types/**',
      ],
    },
  },
  resolve: {
    alias: {
      '@xstate-workflow/core': resolve(__dirname, 'packages/core/src'),
      '@xstate-workflow/frappe-adapter': resolve(__dirname, 'packages/frappe-adapter/src'),
    },
  },
});
