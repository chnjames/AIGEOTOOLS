/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import dns from 'node:dns'

// Windows 上 Node.js 18+ 默认使用 IPv6 优先（::1），导致 Vite 代理连接 IPv4 后端时
// 出现 ECONNREFUSED。强制 IPv4 优先可解决此问题。
dns.setDefaultResultOrder('ipv4first')

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    // 产物分块策略：将大依赖拆分为独立 chunk，避免单个 vendor bundle 过大
    rollupOptions: {
      output: {
        manualChunks(id) {
          // node_modules 中的依赖统一拆分
          if (id.includes('node_modules')) {
            // antd 及其图标库
            if (id.includes('antd') || id.includes('@ant-design/icons') || id.includes('rc-')) {
              return 'antd'
            }
            // echarts 图表库（体积较大，单独拆分）
            if (id.includes('echarts') || id.includes('zrender')) {
              return 'echarts'
            }
            // React 核心
            if (id.includes('react') || id.includes('scheduler')) {
              return 'react'
            }
            // 路由库
            if (id.includes('react-router') || id.includes('@remix-run')) {
              return 'router'
            }
            // 状态管理
            if (id.includes('zustand')) {
              return 'zustand'
            }
            // HTTP 客户端
            if (id.includes('axios')) {
              return 'axios'
            }
            // Markdown 渲染相关
            if (id.includes('react-markdown') || id.includes('remark') || id.includes('micromark') || id.includes('mdast') || id.includes('hast') || id.includes('unist') || id.includes('character-') || id.includes('decode-named') || id.includes('trim-lines') || id.includes('vfile') || id.includes('unified') || id.includes('bail') || id.includes('is-plain-obj') || id.includes('trough') || id.includes('ccount') || id.includes('comma-separated') || id.includes('property-information') || id.includes('space-separated') || id.includes('trim') || id.includes('estree-')) {
              return 'markdown'
            }
            // 时间库
            if (id.includes('dayjs')) {
              return 'dayjs'
            }
            // 其余 node_modules 统一归入 vendor
            return 'vendor'
          }
          return undefined
        },
      },
    },
    // 触发警告的 chunk 大小阈值
    chunkSizeWarningLimit: 1000,
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
})
