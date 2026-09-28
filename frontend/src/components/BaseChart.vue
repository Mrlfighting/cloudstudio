<script setup lang="ts">
/**
 * 通用 ECharts 图表组件：封装 init / setOption / resize / dispose 生命周期。
 * 全量引入 echarts 并注册 wordcloud（供词云图表使用）。
 */
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  option: echarts.EChartsOption
  height?: string
  ariaLabel?: string
}>()

const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let motionPreference: MediaQueryList | null = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(
    {
      ...props.option,
      animation: !(motionPreference?.matches ?? false),
    },
    true,
  )
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
  render()
  window.addEventListener('resize', resize)
  motionPreference.addEventListener('change', render)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  motionPreference?.removeEventListener('change', render)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div
    ref="el"
    class="base-chart"
    role="img"
    :aria-label="ariaLabel || '数据图表'"
    :style="{ width: '100%', height: height || '320px' }"
  />
</template>

<style scoped>
.base-chart { min-width: 0; }
</style>
