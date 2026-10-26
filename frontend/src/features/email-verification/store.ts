/** 账号隔离的邮箱状态机；弹窗、状态查询和原操作续接均在此统一管理。 */
import { computed, ref, shallowRef, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { getErrorMessage } from '@/api/http'
import { cancelEmailRequests, emailApi, retryAfterSeconds } from './api'
import { EmailAccessError, EmailSessionError } from './errors'
import type { EmailStatus } from './types'

export const EMAIL_NOTICE_KEY = 'cloudatelier.email.verified'

export const useEmailVerificationStore = defineStore('email-verification', () => {
  const auth = useAuthStore()
  const owner = ref<number | null>(null)
  const status = shallowRef<EmailStatus | null>(null)
  const checked = ref(false)
  const syncing = ref(false)
  const visible = ref(false)
  const reason = ref('')
  const editing = ref(true)
  const address = ref('')
  const code = ref('')
  const sending = ref(false)
  const confirming = ref(false)
  const statusError = ref('')
  const formError = ref('')
  const notice = ref('')
  const resendAt = ref(0)
  const throttleAt = ref(0)
  const confirmRetryAt = ref(0)
  let epoch = 0
  let statusRevision = 0
  let refreshPromise: Promise<boolean> | null = null
  let gatePromise: Promise<boolean> | null = null
  let settleGate: ((value: boolean) => void) | null = null

  const pending = computed(() => status.value?.pending?.purpose === 'binding' ? status.value.pending : null)
  const canUsePrivate = computed(() => auth.user?.id === owner.value && checked.value
    && !statusError.value && !!status.value?.email && status.value.email_verified)
  const retryAt = computed(() => Math.max(resendAt.value, throttleAt.value))

  function current(id: number, boundary: number): boolean {
    return owner.value === id && auth.user?.id === id && epoch === boundary
  }
  function finish(accepted: boolean): void {
    const resolve = settleGate
    settleGate = null
    gatePromise = null
    visible.value = false
    code.value = ''
    address.value = ''
    formError.value = ''
    sending.value = false
    confirming.value = false
    epoch++
    cancelEmailRequests()
    refreshPromise = null
    syncing.value = false
    resolve?.(accepted)
  }
  function reset(id: number | null): void {
    finish(false)
    owner.value = id
    status.value = null
    checked.value = false
    statusError.value = ''
    reason.value = ''
    resendAt.value = 0
    throttleAt.value = 0
    confirmRetryAt.value = 0
  }
  function applyStatus(value: EmailStatus): void {
    status.value = value
    checked.value = true
    statusError.value = ''
    resendAt.value = value.pending ? Date.now() + Math.max(0, value.pending.retry_after) * 1000 : 0
    if (auth.user?.id === owner.value) {
      auth.setUser({ ...auth.user, email: value.email, email_verified: value.email_verified })
    }
    // 其他标签页验证完成后，仅放行等待验证的操作，不关闭主动换绑表单。
    if (gatePromise && canUsePrivate.value) finish(true)
  }
  function handleError(error: unknown, fallback: string, confirmation = false): void {
    if (error instanceof EmailSessionError) {
      notice.value = error.message
      return
    }
    formError.value = getErrorMessage(error, fallback)
    const seconds = retryAfterSeconds(error)
    if (seconds) (confirmation ? confirmRetryAt : throttleAt).value = Date.now() + seconds * 1000
  }
  async function refresh(): Promise<boolean> {
    if (owner.value == null || auth.user?.id !== owner.value) return false
    if (refreshPromise) return refreshPromise
    const id = owner.value
    const boundary = epoch
    const revision = statusRevision
    syncing.value = true
    const promise = (async () => {
      try {
        const value = await emailApi.status(id)
        if (!current(id, boundary) || revision !== statusRevision) return false
        applyStatus(value)
        return true
      } catch (error) {
        if (error instanceof EmailSessionError) notice.value = error.message
        if (current(id, boundary) && revision === statusRevision && !(error instanceof DOMException && error.name === 'AbortError')) {
          checked.value = false
          statusError.value = getErrorMessage(error, '邮箱状态暂时无法获取，请重试后继续')
        }
        return false
      } finally {
        if (current(id, boundary) && revision === statusRevision) syncing.value = false
      }
    })()
    refreshPromise = promise
    void promise.finally(() => { if (refreshPromise === promise) refreshPromise = null })
    return promise
  }
  function prepareDialog(message: string, change = false): void {
    reason.value = message
    visible.value = true
    editing.value = change || !pending.value
    address.value = pending.value?.email ?? status.value?.email ?? auth.user?.email ?? ''
    code.value = ''
    formError.value = ''
  }
  async function requireVerified(message = '验证邮箱后即可使用此功能'): Promise<boolean> {
    if (!auth.user || owner.value !== auth.user.id) return false
    if (gatePromise) return gatePromise
    const id = owner.value
    const boundary = epoch
    // 每次业务入口核对真实Session和验证状态；并发查询复用同一个请求。
    await refresh()
    if (!current(id, boundary)) return canUsePrivate.value && auth.user?.id === id
    if (canUsePrivate.value) return true
    if (gatePromise) return gatePromise
    gatePromise = new Promise<boolean>((resolve) => { settleGate = resolve })
    prepareDialog(message)
    return gatePromise
  }
  async function assertPrivateAccess(): Promise<void> {
    await refresh()
    if (!canUsePrivate.value) throw new EmailAccessError(statusError.value || undefined)
  }
  async function openSettings(change = false): Promise<void> {
    if (!auth.user) return
    await refresh()
    if (!auth.user || auth.user.id !== owner.value) return
    prepareDialog(change ? '验证新邮箱后完成换绑，原邮箱在此之前继续有效' : '完成邮箱验证，开启完整创作功能', change)
  }
  function editAddress(): void {
    editing.value = true
    code.value = ''
    formError.value = ''
  }
  function resumePending(): void {
    if (!pending.value) return
    address.value = pending.value.email
    editing.value = false
    code.value = ''
    formError.value = ''
  }
  async function sendCode(): Promise<boolean> {
    if (sending.value || confirming.value || owner.value == null || Date.now() < retryAt.value) return false
    const id = owner.value
    const boundary = epoch
    const email = address.value.trim().toLowerCase()
    sending.value = true
    formError.value = ''
    // 老的状态查询不能覆盖刚发出的新申请；写入前后各隔开一个状态版本。
    statusRevision++
    refreshPromise = null
    syncing.value = false
    try {
      const ack = await emailApi.binding(id, email)
      if (!current(id, boundary)) return false
      statusRevision++
      refreshPromise = null
      syncing.value = false
      status.value = {
        email: status.value?.email ?? auth.user?.email ?? null,
        email_verified: status.value?.email_verified ?? false,
        pending: { ...ack, email, purpose: 'binding' },
      }
      resendAt.value = Date.now() + Math.max(0, ack.retry_after) * 1000
      address.value = email
      code.value = ''
      editing.value = false
      return true
    } catch (error) {
      if (current(id, boundary) || error instanceof EmailSessionError) handleError(error, '申请验证码失败，请稍后重试')
      return false
    } finally {
      if (current(id, boundary)) sending.value = false
    }
  }
  async function confirmCode(): Promise<boolean> {
    if (confirming.value || sending.value || owner.value == null || !pending.value
      || Date.now() < confirmRetryAt.value || !/^[0-9]{6}$/.test(code.value)) return false
    const id = owner.value
    const boundary = epoch
    const requestId = pending.value.request_id
    confirming.value = true
    formError.value = ''
    statusRevision++
    refreshPromise = null
    syncing.value = false
    try {
      const result = await emailApi.confirm(id, requestId, code.value)
      if (!current(id, boundary)) return false
      statusRevision++
      // 确认响应是权威结果，不因后续资料刷新失败而误报验证失败。
      applyStatus({ ...result, pending: null })
      if (visible.value) finish(true)
      try {
        localStorage.setItem(EMAIL_NOTICE_KEY, JSON.stringify({ owner: id, stamp: Date.now(), nonce: crypto.randomUUID() }))
      } catch { /* 存储受限时仍可通过切回页面重新查询，不影响本次验证。 */ }
      return true
    } catch (error) {
      if (current(id, boundary) || error instanceof EmailSessionError) {
        handleError(error, '验证码确认失败，请重试', true)
        // 达到后端错误次数上限时，刷新状态即可识别已经失效的申请。
        if ((error as { response?: { status?: number } })?.response?.status === 400) void refresh()
      }
      return false
    } finally {
      if (current(id, boundary)) confirming.value = false
    }
  }
  watch(() => auth.user?.id ?? null, (id) => {
    reset(id)
    if (id != null) void refresh()
  }, { immediate: true, flush: 'sync' })

  return {
    owner, status, checked, syncing, visible, reason, editing, address, code, sending, confirming,
    statusError, formError, notice, pending, retryAt, confirmRetryAt, canUsePrivate,
    refresh, requireVerified, assertPrivateAccess, openSettings, editAddress, resumePending, sendCode, confirmCode,
    defer: () => finish(false),
  }
})
