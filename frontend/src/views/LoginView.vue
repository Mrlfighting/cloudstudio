<script setup lang="ts">
/** 独立登录页：兼容旧链接，表单与全局认证弹窗共用。 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoginForm from '@/components/auth/LoginForm.vue'
import AuthPageShell from '@/components/auth/AuthPageShell.vue'

const router = useRouter()
const route = useRoute()

const initialAccount = computed(() => typeof route.query.account === 'string' ? route.query.account : '')
const redirect = computed(() => {
  const value = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  return value.startsWith('/') && !value.startsWith('//') ? value : '/pictures'
})

function handleSuccess(): void {
  void router.replace(redirect.value)
}

function goRegister(): void {
  void router.push({ path: '/register', query: { redirect: redirect.value } })
}
</script>

<template>
  <AuthPageShell
    mode="login"
    eyebrow="MEMBER SIGN IN"
    title="欢迎回来"
    subtitle="登录云上工坊，继续发现、收藏与创作。"
  >
      <LoginForm :initial-account="initialAccount" @success="handleSuccess" @switch-register="goRegister" />
  </AuthPageShell>
</template>
