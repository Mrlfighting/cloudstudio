<script setup lang="ts">
defineProps<{ label: string; value: string | number; hint?: string }>()
</script>

<template>
  <el-card class="stat-card" shadow="never">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }} <span v-if="hint" class="unit">{{ hint }}</span></div>
  </el-card>
</template>

<style scoped>
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: var(--app-muted); }
.stat-value { margin-top: 8px; font-size: 26px; font-weight: 900; color: var(--app-ink); }
.unit { font-size: 13px; font-weight: 500; color: var(--app-muted); }
</style>
