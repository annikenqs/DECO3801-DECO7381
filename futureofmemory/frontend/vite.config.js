/* eslint-env node */
import { defineConfig, loadEnv } from 'vite';
import { resolve } from 'path';
import fs from 'fs';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const backendOrigin = env.VITE_BACKEND_ORIGIN || 'http://localhost:8000';

  // Collect all .html files from src/html and include index.html
  const htmlDir = resolve(__dirname, 'src/html');
  const htmlFiles = fs.existsSync(htmlDir)
    ? fs
        .readdirSync(htmlDir)
        .filter(f => f.endsWith('.html'))
        .reduce((entries, file) => {
          const name = file.replace('.html', '');
          entries[name] = resolve(htmlDir, file);
          return entries;
        }, {})
    : {};

  // Add index.html as the main entry
  htmlFiles.main = resolve(__dirname, 'index.html');

  return {
    server: {
      port: 5173,
      open: false,
      proxy: {
        '/api': {
          target: backendOrigin,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      rollupOptions: {
        input: htmlFiles,
      },
    },
  };
});
