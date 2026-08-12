<script setup lang="ts">
/**
 * 空值占位：值为空/undefined/null 时显示"未填写"
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    value?: string | number | null
    placeholder?: string
  }>(),
  { placeholder: '未填写' },
)

const isEmpty = computed(() => props.value === undefined || props.value === null || props.value === '')
</script>

<template>
  <span :class="{ 'text-muted': isEmpty }">{{ isEmpty ? placeholder : value }}</span>
</template>

<style scoped>
.text-muted {
  color: #a8abb2;
}
</style>
