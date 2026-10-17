<script setup lang="ts">
// 根组件：认证弹窗独立于路由渲染，确保首次访问受保护深链时也可展示。
import AuthDialog from '@/components/auth/AuthDialog.vue'
import BeadPersistenceBridge from '@/features/bead-pattern/BeadPersistenceBridge.vue'
</script>

<template>
  <BeadPersistenceBridge />
  <router-view />
  <AuthDialog />
</template>
