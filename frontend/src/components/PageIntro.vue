<script setup lang="ts">
withDefaults(
  defineProps<{
    eyebrow?: string
    title: string
    subtitle?: string
  }>(),
  { eyebrow: 'WORKSPACE', subtitle: '' },
)
</script>

<template>
  <div class="page-intro">
    <div class="eyebrow">{{ eyebrow }}</div>
    <h2 class="page-title">{{ title }}</h2>
    <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
  </div>
</template>

<style scoped>
.page-intro { margin-bottom: 22px; }
.eyebrow { color: #b16880; font-size: 11px; font-weight: 800; letter-spacing: 2px; margin-bottom: 10px; }
.page-title { margin: 0; }
.page-subtitle { margin: 10px 0 0; color: var(--app-muted); font-size: 15px; }
</style>
