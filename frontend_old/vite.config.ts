import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../xstate_workflow/public/js',
    emptyOutDir: false,
    cssCodeSplit: false,
    lib: {
      entry: path.resolve(__dirname, 'src/main.tsx'),
      name: 'WorkflowBuilder',
      fileName: () => 'workflow_builder.bundle.js',
      formats: ['iife']
    },
    rollupOptions: {
      output: {
        exports: 'named',
        globals: {},
        assetFileNames: 'workflow_builder[extname]'
      }
    }
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production')
  }
});
