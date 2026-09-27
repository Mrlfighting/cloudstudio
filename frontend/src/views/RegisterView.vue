<script setup lang="ts">
/** 独立注册页：兼容旧链接，注册成功后进入共享登录表单。 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import SiteFooter from '@/components/SiteFooter.vue'

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
  <div class="auth-page">
    <div class="auth-decoration" aria-hidden="true"><span></span><i></i><b></b></div>
    <el-card class="auth-card">
      <template #header>
        <div class="auth-heading">创建你的空间</div>
        <div class="auth-kicker">加入云上工坊，收藏每一份灵感</div>
      </template>
      <RegisterForm @success="handleSuccess" @switch-login="goLogin" />
    </el-card>
    <SiteFooter fixed />
  </div>
</template>
