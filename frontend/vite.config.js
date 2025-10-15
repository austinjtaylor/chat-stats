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
        settings: path.resolve(__dirname, 'settings.html'),
        pricing: path.resolve(__dirname, 'pricing.html'),
      },
      output: {
        manualChunks: {
          // Group API and utilities together
          'utils': [
            './src/api/client.ts',
            './src/utils/dom.ts',
            './src/utils/format.ts'
          ]
        }
      }
    },
    // Optimize CSS
    cssCodeSplit: true,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false,  // Temporarily enabled for debugging
        drop_debugger: true
      }
    }
  },
  server: {
    port: 3000,
    open: true,
    // https: true,  // Disabled for now - enable only when testing Stripe payment entry
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