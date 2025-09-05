import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    open: false,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
      },
      '/agent': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-avatar', '@radix-ui/react-label', '@radix-ui/react-scroll-area'],
        }
      }
    }
  },
  optimizeDeps: {
    include: ['@microsoft/fetch-event-source', 'lucide-react']
  },
  preview: {
    allowedHosts: [
      'healthcheck.railway.app',
      '*.up.railway.app',
      // Railway deployment domain
      ...(process.env.RAILWAY_STATIC_URL ? (() => {
        try {
          return [new URL(process.env.RAILWAY_STATIC_URL).hostname];
        } catch {
          return [];
        }
      })() : []),
      // Additional domains from env var
      ...(process.env.VITE_ALLOWED_HOSTS ?
        process.env.VITE_ALLOWED_HOSTS.split(',') : [])
    ]
  }
})
