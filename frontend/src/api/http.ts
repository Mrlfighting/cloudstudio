/**
 * Axios 实例与拦截器
 * - 会话认证：withCredentials 携带 cookie（开发经 Vite 代理同源）
 * - CSRF：POST/PATCH/DELETE 自动注入 X-CSRF-Token（读 JS 可读的 csrf_token cookie）
 * - 401：登录失效 → 清状态并跳转登录页（登录接口自身的 401/429 不跳转）
 * - 403 + X-CSRF-Error：CSRF token 过期 → 刷新后重放一次
 */
import axios from 'axios'
import { getCookie, setCookie } from '@/utils/cookies'

export const http = axios.create({
  // 后端路由在 /api/v1/... 下，baseURL 直接含版本段
  baseURL: import.meta.env.VITE_API_BASE ?? '/api/v1',
  withCredentials: true,
  timeout: 15000,
})

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete'])

// 请求拦截器：不安全方法注入 CSRF 头
http.interceptors.request.use((config) => {
  const method = (config.method ?? 'get').toLowerCase()
  if (UNSAFE_METHODS.has(method)) {
    const token = getCookie('csrf_token')
    if (token) {
      if (typeof config.headers.set === 'function') {
        config.headers.set('X-CSRF-Token', token)
      } else {
        config.headers['X-CSRF-Token'] = token
      }
    }
  }
  return config
})

// 响应拦截器：401 跳转 / 403 CSRF 刷新重试
http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { response, config } = error
    if (!response || !config) return Promise.reject(error)

    // CSRF token 过期恢复：刷新后重放一次
    if (response.status === 403 && response.headers['x-csrf-error'] && !config._csrfRetried) {
      config._csrfRetried = true
      try {
        const { data } = await axios.post(
          '/api/v1/auth/refresh-csrf',
          null,
          { withCredentials: true },
        )
        setCookie('csrf_token', data.csrf_token)
        if (typeof config.headers.set === 'function') {
          config.headers.set('X-CSRF-Token', data.csrf_token)
        } else {
          config.headers['X-CSRF-Token'] = data.csrf_token
        }
        return http(config)
      } catch {
        /* 刷新失败，落到通用 403 处理 */
      }
    }

    // 401：登录接口自身不跳转；其余清状态并跳登录页
    if (response.status === 401) {
      const url = config.url ?? ''
      const isLoginCall = url.includes('/auth/login')
      const onLoginRoute = window.location.pathname.startsWith('/login')
      if (!isLoginCall && !onLoginRoute) {
        const { useAuthStore } = await import('@/stores/auth')
        useAuthStore().reset()
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?redirect=${redirect}`
      }
    }

    return Promise.reject(error)
  },
)

/** 统一的错误消息提取（后端 HTTPException 返回 {detail}；422 被脱敏为通用串） */
export function getErrorMessage(err: unknown, fallback = '操作失败，请重试'): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.length) return detail
  const status = (err as { response?: { status?: number } })?.response?.status
  if (status === 401) return '登录已失效，请重新登录'
  if (status === 403) return '没有权限执行此操作'
  if (status === 422) return '输入有误，请检查后重试'
  if (status === 429) return '操作过于频繁，请稍后再试'
  return fallback
}
