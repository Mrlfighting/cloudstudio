/** 邮箱专用传输：保留Cookie/CSRF，禁止401登录后自动重放验证码写入。 */
import axios, { type AxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { getCookie, setCookie } from '@/utils/cookies'
import { EmailSessionError } from './errors'
import type { EmailConfirmation, EmailRequestAck, EmailStatus } from './types'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '/api/v1',
  withCredentials: true,
  timeout: 15000,
})
let generation = 0
const controllers = new Set<AbortController>()

export function cancelEmailRequests(): void {
  generation++
  for (const controller of controllers) controller.abort()
  controllers.clear()
}

async function request<T>(owner: number, config: AxiosRequestConfig): Promise<T> {
  const auth = useAuthStore()
  const boundary = generation
  const controller = new AbortController()
  controllers.add(controller)
  function check(): void {
    if (controller.signal.aborted || boundary !== generation || auth.user?.id !== owner) {
      throw new DOMException('账号或验证操作已变更', 'AbortError')
    }
  }
  async function send(retried = false): Promise<T> {
    check()
    try {
      const response = await client.request<T>({
        ...config,
        signal: controller.signal,
        headers: {
          ...config.headers,
          'X-Expected-User-ID': String(owner),
          'X-CSRF-Token': getCookie('csrf_token') ?? '',
        },
      })
      check()
      return response.data
    } catch (error) {
      check()
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401 || error.response?.headers['x-email-session-changed']) {
          const message = error.response.status === 401
            ? '登录已失效，请重新登录后继续验证邮箱'
            : '登录账号已在其他页面变更，本次邮箱操作已取消'
          auth.reset()
          throw new EmailSessionError(message)
        }
        if (!retried && error.response?.status === 403 && error.response.headers['x-csrf-error']) {
          try {
            const fresh = await client.post<{ csrf_token: string }>('/auth/refresh-csrf', null, { signal: controller.signal })
            check()
            setCookie('csrf_token', fresh.data.csrf_token)
          } catch (refreshError) {
            check()
            if (axios.isAxiosError(refreshError) && refreshError.response?.status === 401) {
              auth.reset()
              throw new EmailSessionError('登录已失效，请重新登录后继续验证邮箱')
            }
            throw refreshError
          }
          return send(true)
        }
      }
      throw error
    }
  }
  try {
    return await send()
  } finally {
    controllers.delete(controller)
  }
}

export const emailApi = {
  status: (owner: number) => request<EmailStatus>(owner, { url: '/email/status' }),
  binding: (owner: number, email: string) => request<EmailRequestAck>(owner, {
    method: 'post', url: '/email/binding/request', data: { email },
  }),
  confirm: (owner: number, requestId: string, code: string) => request<EmailConfirmation>(owner, {
    method: 'post', url: '/email/binding/confirm', data: { request_id: requestId, code },
  }),
}

/** 限流时间以服务端为准，同时支持秒数和HTTP日期。 */
export function retryAfterSeconds(error: unknown): number {
  if (!axios.isAxiosError(error) || error.response?.status !== 429) return 0
  const value = error.response.headers['retry-after']
  const seconds = Number(value)
  if (Number.isFinite(seconds) && seconds > 0) return Math.ceil(seconds)
  const deadline = typeof value === 'string' ? Date.parse(value) : NaN
  return Number.isFinite(deadline) ? Math.max(0, Math.ceil((deadline - Date.now()) / 1000)) : 0
}
