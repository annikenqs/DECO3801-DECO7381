/* eslint-env node */
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  // eslint-disable-next-line no-undef
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const backendOrigin = env.VITE_BACKEND_ORIGIN || 'http://localhost:8000';

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
  };
});
