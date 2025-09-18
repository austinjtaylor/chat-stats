import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  root: '.',
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
        players: path.resolve(__dirname, 'stats/players.html'),
        teams: path.resolve(__dirname, 'stats/teams.html'),
        gameDetail: path.resolve(__dirname, 'stats/game-detail.html'),
      },
      output: {
        manualChunks: {
          // Group API and utilities together
          'utils': [
            './js/api/client.js',
            './js/utils/dom.js',
            './js/utils/format.js'
          ]
        }
      }
    },
    // Optimize CSS
    cssCodeSplit: true,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      // Proxy API requests to backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  css: {
    postcss: {
      plugins: [
        require('postcss-import'),
        require('postcss-nesting'),
        require('autoprefixer')
      ]
    }
  },
  optimizeDeps: {
    include: ['marked']
  }
});