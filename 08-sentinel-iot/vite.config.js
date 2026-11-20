import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: path.join(projectRoot, 'web'),
  plugins: [react()],
  server: {
    port: 5109,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:5108',
      '/ws': {
        target: 'ws://localhost:5108',
        ws: true,
      },
    },
  },
  build: {
    outDir: path.join(projectRoot, 'dist'),
    emptyOutDir: true,
    sourcemap: false,
    target: 'es2022',
  },
});
