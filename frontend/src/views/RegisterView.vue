<script setup lang="ts">
/** 独立注册页：兼容旧链接，注册成功后进入共享登录表单。 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import AuthPageShell from '@/components/auth/AuthPageShell.vue'

const router = useRouter()
const route = useRoute()

const redirect = computed(() => {
  const value = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  return value.startsWith('/') && !value.startsWith('//') ? value : '/pictures'
})

function handleSuccess(account: string): void {
  void router.push({ path: '/login', query: { account, redirect: redirect.value } })
}

function goLogin(): void {
  void router.push({ path: '/login', query: { redirect: redirect.value } })
}
</script>

<template>
  <AuthPageShell
    mode="register"
    eyebrow="JOIN CLOUD ATELIER"
    title="创建你的空间"
    subtitle="加入云上工坊，收藏每一份值得记住的灵感。"
  >
      <RegisterForm @success="handleSuccess" @switch-login="goLogin" />
  </AuthPageShell>
</template>
