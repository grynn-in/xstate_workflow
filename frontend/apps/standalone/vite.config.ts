import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, '../../../xstate_workflow/public/js'),
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, 'src/main.tsx'),
      name: 'XStateWorkflowBuilder',
      fileName: 'workflow_builder.standalone',
      formats: ['iife'],
    },
    rollupOptions: {
      external: [],
      output: {
        globals: {},
        assetFileNames: 'workflow_builder.[ext]',
      },
    },
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
});
