<script setup lang="ts">
/**
 * 角色标签：user → 灰"用户"，admin → 绿"管理员"
 */
import { computed } from 'vue'
import type { UserRole } from '@/types/user'

const props = defineProps<{
  role: UserRole
}>()

const label = computed(() => (props.role === 'admin' ? '管理员' : '用户'))
const type = computed<'success' | 'info'>(() => (props.role === 'admin' ? 'success' : 'info'))
</script>

<template>
  <el-tag :type="type" size="small" effect="light">{{ label }}</el-tag>
</template>
