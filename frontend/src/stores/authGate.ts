/**
 * 全局认证门：游客触发受保护操作时打开同一个认证弹窗。
 * Promise 解析器保留在 Pinia 状态外，避免不可序列化对象进入状态树。
 */
import { defineStore } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useEmailVerificationStore } from '@/features/email-verification/store'

export type AuthDialogMode = 'login' | 'register'

export interface AuthenticationRequest {
  mode?: AuthDialogMode
  reason?: string
}

let pendingPromise: Promise<boolean> | null = null
let settlePending: ((authenticated: boolean) => void) | null = null
let completionSerial = 0

function resolvePending(authenticated: boolean): void {
  settlePending?.(authenticated)
  settlePending = null
  pendingPromise = null
}

export const useAuthGateStore = defineStore('auth-gate', {
  state: () => ({
    visible: false,
    mode: 'login' as AuthDialogMode,
    reason: '',
    prefilledAccount: '',
    continuationUrl: '',
  }),

  actions: {
    requireAuthentication(request: AuthenticationRequest = {}): Promise<boolean> {
      const auth = useAuthStore()
      if (auth.isAuthenticated) {
        return pendingPromise ?? useEmailVerificationStore().requireVerified(request.reason || '验证邮箱后即可继续此操作')
      }

      this.mode = request.mode ?? this.mode
      this.reason = request.reason ?? this.reason
      this.continuationUrl = ''
      this.visible = true

      if (!pendingPromise) {
        pendingPromise = new Promise<boolean>((resolve) => {
          settlePending = resolve
        })
      }
      return pendingPromise
    },

    switchMode(mode: AuthDialogMode): void {
      this.mode = mode
    },

    registrationCompleted(account: string): void {
      this.prefilledAccount = account
      this.mode = 'login'
    },

    async authenticationCompleted(): Promise<void> {
      const auth = useAuthStore()
      const id = auth.user?.id
      const serial = ++completionSerial
      // 关闭登录表单但暂不放行原操作，接着显示独立的邮箱验证弹窗。
      this.visible = false
      const verified = await useEmailVerificationStore().requireVerified(this.reason || '验证邮箱后继续使用完整功能')
      if (serial !== completionSerial) return
      if (auth.user?.id !== id) { this.cancelAuthentication(); return }
      if (!verified) { this.cancelAuthentication(); return }
      this.reason = ''
      this.prefilledAccount = ''
      this.continuationUrl = ''
      resolvePending(true)
    },

    cancelAuthentication(): void {
      completionSerial++
      this.visible = false
      this.reason = ''
      this.prefilledAccount = ''
      this.continuationUrl = ''
      resolvePending(false)
    },

    showDownloadFallback(url: string): void {
      this.continuationUrl = url
      this.reason = '账号与邮箱验证已完成，请点击下方按钮继续下载'
      this.visible = true
    },

    closeContinuation(): void {
      this.visible = false
      this.reason = ''
      this.continuationUrl = ''
    },
  },
})
