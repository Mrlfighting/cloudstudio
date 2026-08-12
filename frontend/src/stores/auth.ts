/**
 * 认证状态（Pinia）
 * - 应用启动时 initialize()：check-auth + GET /me 补齐完整用户
 * - login/logout：与会话 cookie 协同
 */
import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'
import type { UserRead } from '@/types/user'
import { getCookie, setCookie } from '@/utils/cookies'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as UserRead | null,
    csrfToken: null as string | null,
    /** 首次启动检查是否已完成（避免每次导航都重复 check-auth） */
    initialized: false,
  }),

  getters: {
    isAuthenticated: (state): boolean => !!state.user,
    isAdmin: (state): boolean => state.user?.user_role === 'admin' || state.user?.is_superuser === true,
  },

  actions: {
    /** 启动检查：check-auth → 已登录则 GET /me 补齐完整用户 */
    async initialize(): Promise<void> {
      if (this.initialized) return
      try {
        const res = await authApi.checkAuth()
        if (res.authenticated) {
          this.user = await userApi.getMe()
        }
        this.csrfToken = getCookie('csrf_token')
      } catch {
        // 网络异常时保持未登录（放行到登录页）
      } finally {
        this.initialized = true
      }
    },

    /** 登录：拿到 csrf_token 后镜像到 cookie，并直接拉取完整用户。
     *
     * 注意：不能用 initialize() —— 它带幂等守卫（initialized 为 true 时直接返回），
     * 而打开登录页时路由守卫已初始化过一次，会导致 user 仍为 null、登录被误判失败。
     */
    async login(account: string, password: string): Promise<UserRead> {
      const { csrf_token } = await authApi.login(account, password)
      setCookie('csrf_token', csrf_token)
      this.csrfToken = csrf_token
      this.user = await userApi.getMe()
      return this.user
    },

    /** 注销：无论如何都清空本地状态 */
    async logout(): Promise<void> {
      try {
        await authApi.logout()
      } catch {
        // 会话已过期等场景：仍继续清理本地状态
      } finally {
        this.reset()
      }
    },

    async refreshCsrf(): Promise<void> {
      const { csrf_token } = await authApi.refreshCsrf()
      setCookie('csrf_token', csrf_token)
      this.csrfToken = csrf_token
    },

    setUser(user: UserRead): void {
      this.user = user
    },

    reset(): void {
      this.user = null
      this.csrfToken = null
      this.initialized = true
    },
  },
})
