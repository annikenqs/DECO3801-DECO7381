/* eslint-env node */
import {defineConfig} from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    open: false,
    proxy: {
      '/api': {
        // eslint-disable-next-line no-undef
        target: process.env.VITE_BACKEND_ORIGIN || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
});
