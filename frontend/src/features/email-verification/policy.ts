/** 通过独立前置拦截接入旧业务；公开浏览和认证初始化不得被验证流程阻塞。 */
import { http } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { useEmailVerificationStore } from './store'
import { EmailAccessError } from './errors'

export function isEmailExemptRequest(url: string, method = 'get'): boolean {
  const path = new URL(url, 'https://frontend.invalid').pathname.replace(/^\/api\/v1(?=\/)/, '')
  const verb = method.toLowerCase()
  if (path.startsWith('/auth/')) return true
  if (verb === 'post' && path === '/users/register') return true
  if (verb === 'get' && path === '/users/me') return true
  if (path === '/email/status' || path === '/email/binding/request' || path === '/email/binding/confirm') return true
  return verb === 'get' && (path === '/pictures/' || /^\/pictures\/\d+$/.test(path))
}

export function installEmailRequestPolicy(): void {
  http.interceptors.request.use(async (config) => {
    if (isEmailExemptRequest(config.url ?? '', config.method)) return config
    const auth = useAuthStore()
    if (!auth.user) return config
    const id = auth.user.id
    await useEmailVerificationStore().assertPrivateAccess()
    if (auth.user?.id !== id) throw new EmailAccessError('登录账号已变更，请重新发起操作')
    return config
  })
}
