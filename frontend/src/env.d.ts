/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API 基础路径（开发 /api 走 Vite 代理，生产同域 nginx 转发） */
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    /** CSRF 刷新后已重放标记（防止无限重试） */
    _csrfRetried?: boolean
  }
}

export {}
