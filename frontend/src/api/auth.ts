/**
 * 认证相关 API
 */
import { http } from './http'
import type {
  CheckAuthResponse,
  LoginResult,
  MessageResponse,
  RegisterPayload,
  UserRead,
} from '@/types/user'

export const authApi = {
  /** 登录：必须表单编码，字段名固定 username/password（OAuth2PasswordRequestForm） */
  login(account: string, password: string): Promise<LoginResult> {
    const body = new URLSearchParams({ username: account, password })
    return http
      .post<LoginResult>('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      .then((r) => r.data)
  },

  /** 注册：返回用户但【不建立会话】 */
  register(payload: RegisterPayload): Promise<UserRead> {
    return http.post<UserRead>('/users/register', payload).then((r) => r.data)
  },

  /** 注销：CSRF 头由拦截器自动注入 */
  logout(): Promise<MessageResponse> {
    return http.post<MessageResponse>('/auth/logout').then((r) => r.data)
  },

  /** 检查登录态：匿名也返回 200（authenticated: false） */
  checkAuth(): Promise<CheckAuthResponse> {
    return http.get<CheckAuthResponse>('/auth/check-auth').then((r) => r.data)
  },

  /** 刷新 CSRF token（只需会话 cookie，无需 CSRF 头） */
  refreshCsrf(): Promise<LoginResult> {
    return http.post<LoginResult>('/auth/refresh-csrf').then((r) => r.data)
  },
}
