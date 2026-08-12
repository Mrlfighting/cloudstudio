<script setup lang="ts">
/**
 * 用户头像：有真实头像显示图片，否则回退到昵称首字
 */
import { computed, ref, watch } from 'vue'
import type { UserRead } from '@/types/user'

const props = withDefaults(
  defineProps<{
    user: UserRead
    size?: number
  }>(),
  { size: 40 },
)

// 后端模型默认占位头像视为"未设置"
const PLACEHOLDER_URLS = ['https://profileimageurl.com', 'https://www.profileimageurl.com']

const imgFailed = ref(false)

const displayUrl = computed(() => {
  const url = props.user?.profile_image_url ?? ''
  if (!url || PLACEHOLDER_URLS.includes(url)) return ''
  return url
})

watch(
  () => props.user?.profile_image_url,
  () => {
    imgFailed.value = false
  },
)

const fallbackText = computed(() => {
  const name = props.user?.name?.trim() ?? ''
  return name ? name.charAt(0).toUpperCase() : '?'
})
</script>

<template>
  <el-avatar
    v-if="displayUrl && !imgFailed"
    :src="displayUrl"
    :size="size"
    @error="imgFailed = true"
  />
  <el-avatar v-else :size="size">{{ fallbackText }}</el-avatar>
</template>
