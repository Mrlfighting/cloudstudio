<script setup lang="ts">
/** 全站只挂载一次：恢复状态、跨标签页刷新及失效后的私有视图清理。 */
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { EMAIL_NOTICE_KEY, useEmailVerificationStore } from './store'
import EmailVerificationDialog from './EmailVerificationDialog.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const email = useEmailVerificationStore()
const privateRoute = () => route.meta.requiresAuth && route.name !== 'profile'
let lastRefresh = 0
function refresh(): void {
  if (!auth.user || document.visibilityState === 'hidden' || Date.now() - lastRefresh < 500) return
  lastRefresh = Date.now()
  void email.refresh()
}
function storage(event: StorageEvent): void {
  if (event.key !== EMAIL_NOTICE_KEY || !event.newValue || !auth.user) return
  try {
    const data = JSON.parse(event.newValue) as { owner?: number }
    // 通知是一次性同步，不是后台轮询；即使标签页隐藏，也先重新核对服务端。
    if (data.owner === auth.user.id) { lastRefresh = Date.now(); void email.refresh() }
  } catch { /* 不把不可信的通知内容作为认证结果。 */ }
}
watch(() => auth.user?.id, (id, old) => {
  if (old != null && old !== id && privateRoute()) void router.replace('/pictures')
})
watch(() => [email.canUsePrivate, email.checked, email.statusError] as const, ([allowed, checked, error]) => {
  if (auth.user && !allowed && (checked || error) && privateRoute()) {
    void router.replace('/pictures')
    void email.requireVerified('请先完成邮箱验证，再继续使用私有功能')
  }
})
watch(() => email.notice, (message) => {
  if (message) { ElMessage.warning(message); email.notice = '' }
})
onMounted(() => {
  window.addEventListener('focus', refresh)
  window.addEventListener('storage', storage)
  document.addEventListener('visibilitychange', refresh)
})
onBeforeUnmount(() => {
  window.removeEventListener('focus', refresh)
  window.removeEventListener('storage', storage)
  document.removeEventListener('visibilitychange', refresh)
})
</script>

<template><EmailVerificationDialog /></template>
