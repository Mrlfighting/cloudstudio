<script setup lang="ts">
/** 全局登录/注册弹窗，同时承接受保护路由的登录后跳转。 */
import { watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import LoginForm from '@/components/auth/LoginForm.vue'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import { useAuthGateStore, type AuthDialogMode } from '@/stores/authGate'

const route = useRoute()
const router = useRouter()
const gate = useAuthGateStore()
let routePromptActive = false

function firstQueryValue(value: unknown): string {
  if (Array.isArray(value)) return typeof value[0] === 'string' ? value[0] : ''
  return typeof value === 'string' ? value : ''
}

function isSafeInternalPath(path: string): boolean {
  return path.startsWith('/') && !path.startsWith('//')
}

function cleanAuthQuery(): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  for (const [key, value] of Object.entries(route.query)) {
    if (key === 'auth' || key === 'redirect' || key === 'authReason' || value === undefined) continue
    query[key] = Array.isArray(value) ? value.map((item) => item ?? '') : value ?? ''
  }
  return query
}

watch(
  () => [route.query.auth, route.query.redirect, route.query.authReason] as const,
  async ([authQuery, redirectQuery, reasonQuery]) => {
    const mode = firstQueryValue(authQuery)
    if (mode !== 'login' && mode !== 'register') {
      if (routePromptActive) gate.cancelAuthentication()
      return
    }
    if (routePromptActive) return

    routePromptActive = true
    const redirect = firstQueryValue(redirectQuery)
    const authenticated = await gate.requireAuthentication({
      mode: mode as AuthDialogMode,
      reason: firstQueryValue(reasonQuery) || '登录后继续访问该功能',
    })

    const promptStillCurrent = firstQueryValue(route.query.auth) === mode
      && firstQueryValue(route.query.redirect) === redirect
    if (promptStillCurrent) {
      if (authenticated && isSafeInternalPath(redirect)) {
        await router.replace(redirect)
      } else {
        await router.replace({ path: route.path, query: cleanAuthQuery(), hash: route.hash })
      }
    }
    routePromptActive = false
  },
  { immediate: true },
)

function handleVisibilityChange(visible: boolean): void {
  if (!visible) gate.cancelAuthentication()
}

function handleLoginSuccess(): void {
  gate.authenticationCompleted()
}

function handleRegisterSuccess(account: string): void {
  gate.registrationCompleted(account)
}

function continueDownload(): void {
  if (!gate.continuationUrl) return
  window.open(gate.continuationUrl, '_blank', 'noopener')
  gate.closeContinuation()
}
</script>

<template>
  <el-dialog
    :model-value="gate.visible"
    width="min(460px, calc(100vw - 28px))"
    class="auth-dialog"
    append-to-body
    destroy-on-close
    align-center
    :show-close="true"
    @update:model-value="handleVisibilityChange"
  >
    <template #header>
      <div class="dialog-heading">
        <span class="dialog-mark" aria-hidden="true">
          <svg viewBox="0 0 48 48">
            <path class="dialog-mark__cloud" d="M14.7 35.1a6.7 6.7 0 0 1-1.1-13.3 10.6 10.6 0 0 1 20.2 2.6 5.5 5.5 0 0 1-.3 10.9H14.7Z" />
            <path class="dialog-mark__spark" d="M35.8 9.6c.5 3 1.9 4.4 4.8 4.9-2.9.5-4.3 1.9-4.8 4.8-.5-2.9-1.9-4.3-4.8-4.8 2.9-.5 4.3-1.9 4.8-4.9Z" />
            <circle class="dialog-mark__dot" cx="13" cy="13" r="2.2" />
          </svg>
        </span>
        <div>
          <h2>{{ gate.continuationUrl ? '继续下载' : gate.mode === 'login' ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ gate.reason || (gate.mode === 'login' ? '登录云上工坊，继续发现灵感' : '注册后即可使用完整功能') }}</p>
        </div>
      </div>
    </template>

    <div v-if="gate.continuationUrl" class="continuation-panel">
      <el-icon :size="36"><CircleCheckFilled /></el-icon>
      <p>浏览器阻止了自动打开新窗口，请点击按钮继续。</p>
      <el-button type="primary" @click="continueDownload">继续下载</el-button>
    </div>

    <LoginForm
      v-else-if="gate.mode === 'login'"
      :initial-account="gate.prefilledAccount"
      @success="handleLoginSuccess"
      @switch-register="gate.switchMode('register')"
    />
    <RegisterForm
      v-else
      @success="handleRegisterSuccess"
      @switch-login="gate.switchMode('login')"
    />
  </el-dialog>
</template>

<style>
.auth-dialog { border-radius: 22px; overflow: hidden; }
.auth-dialog .el-dialog__header { padding: 26px 28px 10px; margin: 0; }
.auth-dialog .el-dialog__body { padding: 18px 28px 28px; }
.dialog-heading { display: flex; align-items: center; gap: 14px; padding-right: 24px; }
.dialog-mark { position: relative; width: 42px; height: 42px; display: grid; place-items: center; flex: 0 0 42px; overflow: hidden; border: 1px solid rgba(255,255,255,.92); border-radius: 14px; background: radial-gradient(circle at 25% 20%,rgba(255,255,255,.72),transparent 28%),linear-gradient(145deg,#82d3ef 3%,#aaa9ed 50%,#f58daf 100%); box-shadow: 0 9px 20px rgba(102,151,207,.23),inset 0 1px 0 rgba(255,255,255,.72); transform: rotate(-2deg); }
.dialog-mark::after { position: absolute; inset: 3px; content: ''; pointer-events: none; border: 1px solid rgba(255,255,255,.24); border-radius: 10px; }
.dialog-mark svg { position: relative; z-index: 1; width: 35px; height: 35px; }
.dialog-mark__cloud { fill: rgba(255,255,255,.97); filter: drop-shadow(0 2px 2px rgba(76,99,150,.16)); }
.dialog-mark__spark { fill: #fff1a8; }
.dialog-mark__dot { fill: rgba(255,255,255,.78); }
.dialog-heading h2 { margin: 0; color: var(--app-ink); font-size: 24px; }
.dialog-heading p { margin: 6px 0 0; color: var(--app-muted); font-size: 13px; line-height: 1.5; }
.continuation-panel { display: grid; justify-items: center; gap: 14px; padding: 14px 0 4px; text-align: center; color: var(--app-text); }
.continuation-panel > .el-icon { color: var(--el-color-success); }
.continuation-panel p { margin: 0; }
@media (max-width: 560px) {
  .auth-dialog .el-dialog__header { padding: 22px 20px 8px; }
  .auth-dialog .el-dialog__body { padding: 16px 20px 24px; }
  .dialog-heading { align-items: flex-start; gap: 11px; padding-right: 18px; }
  .dialog-mark { width: 38px; height: 38px; flex-basis: 38px; border-radius: 13px; }
  .dialog-mark svg { width: 32px; height: 32px; }
  .dialog-heading h2 { font-size: 21px; }
  .dialog-heading p { font-size: 12px; overflow-wrap: anywhere; }
}
</style>
