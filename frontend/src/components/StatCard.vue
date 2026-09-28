<script setup lang="ts">
import type { Component } from 'vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    hint?: string
    description?: string
    icon?: Component
    accent?: 'rose' | 'sky' | 'mint' | 'lavender'
    decimals?: number
    delay?: number
  }>(),
  {
    hint: '',
    description: '',
    icon: undefined,
    accent: 'rose',
    decimals: 0,
    delay: 0,
  },
)

const animatedValue = ref<string | number>(typeof props.value === 'number' ? 0 : props.value)
let animationFrame = 0

const formattedValue = computed(() => {
  if (typeof animatedValue.value !== 'number') return animatedValue.value
  return animatedValue.value.toLocaleString('zh-CN', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals,
  })
})

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function animateValue(target: number): void {
  cancelAnimationFrame(animationFrame)

  if (prefersReducedMotion()) {
    animatedValue.value = target
    return
  }

  const startValue = typeof animatedValue.value === 'number' ? animatedValue.value : 0
  const startedAt = performance.now()
  const duration = 760

  const update = (now: number) => {
    const progress = Math.min(1, (now - startedAt) / duration)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedValue.value = startValue + (target - startValue) * eased
    if (progress < 1) animationFrame = requestAnimationFrame(update)
  }

  animationFrame = requestAnimationFrame(update)
}

watch(
  () => props.value,
  (value) => {
    if (typeof value === 'number') animateValue(value)
    else animatedValue.value = value
  },
  { immediate: true },
)

onBeforeUnmount(() => cancelAnimationFrame(animationFrame))
</script>

<template>
  <article
    class="stat-card analytics-reveal"
    :class="`stat-card--${accent}`"
    :style="{ '--reveal-delay': `${delay}ms` }"
  >
    <div class="stat-card__top">
      <span v-if="icon" class="stat-card__icon" aria-hidden="true">
        <el-icon :size="19"><component :is="icon" /></el-icon>
      </span>
      <span class="stat-card__spark" aria-hidden="true"></span>
    </div>
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">
      {{ formattedValue }}
      <span v-if="hint" class="unit">{{ hint }}</span>
    </div>
    <p v-if="description" class="stat-description">{{ description }}</p>
  </article>
</template>

<style scoped>
.stat-card {
  --stat-accent: #ec7296;
  --stat-soft: #fff0f5;
  position: relative;
  min-height: 154px;
  padding: 20px 22px;
  overflow: hidden;
  border: 1px solid rgba(224, 228, 236, 0.92);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 34px rgba(39, 45, 58, 0.07);
  backdrop-filter: blur(16px);
  transition: transform 0.32s cubic-bezier(.22, 1, .36, 1), box-shadow 0.32s ease, border-color 0.32s ease;
}

.stat-card::before {
  content: '';
  position: absolute;
  width: 132px;
  height: 132px;
  right: -58px;
  bottom: -70px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--stat-accent) 32%, transparent), transparent 68%);
  transition: transform 0.45s cubic-bezier(.22, 1, .36, 1);
}

.stat-card:hover {
  transform: translateY(-8px) rotate(-0.3deg);
  border-color: color-mix(in srgb, var(--stat-accent) 38%, #e1e5ed);
  box-shadow: 0 22px 50px color-mix(in srgb, var(--stat-accent) 18%, transparent);
}

.stat-card:hover::before { transform: scale(1.35); }
.stat-card--sky { --stat-accent: #62c4e9; --stat-soft: #eaf9ff; }
.stat-card--mint { --stat-accent: #68cdb5; --stat-soft: #e9faf6; }
.stat-card--lavender { --stat-accent: #9b89df; --stat-soft: #f1edff; }

.stat-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 38px;
  margin-bottom: 8px;
}

.stat-card__icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  color: var(--stat-accent);
  background: var(--stat-soft);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--stat-accent) 10%, transparent);
}

.stat-card__spark {
  width: 7px;
  height: 7px;
  margin-right: 2px;
  border-radius: 50%;
  background: var(--stat-accent);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--stat-accent) 12%, transparent);
  animation: stat-pulse 2.4s ease-in-out infinite;
}

.stat-label { color: #7e8795; font-size: 13px; font-weight: 700; }
.stat-value {
  position: relative;
  z-index: 1;
  min-height: 39px;
  margin-top: 6px;
  color: #171b22;
  font-size: clamp(26px, 2.3vw, 34px);
  line-height: 1.15;
  font-weight: 900;
  letter-spacing: -1px;
}
.unit { margin-left: 3px; color: #8c95a2; font-size: 13px; font-weight: 600; letter-spacing: 0; }
.stat-description { margin: 8px 0 0; color: #a0a8b3; font-size: 12px; line-height: 1.5; }

@keyframes stat-pulse {
  0%, 100% { transform: scale(.82); opacity: .55; }
  50% { transform: scale(1.08); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .stat-card, .stat-card::before { transition: none; }
  .stat-card:hover { transform: none; }
  .stat-card__spark { animation: none; }
}
</style>
