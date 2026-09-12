<script setup lang="ts">
/**
 * 图片裁剪框：在图片上拖拽出矩形框，实时（节流）emit 原图像素坐标的裁剪区域。
 */
import { computed, reactive, ref, watch } from 'vue'
import type { CropRect } from '@/types/picture'

const visible = defineModel<boolean>({ default: false })
const props = defineProps<{
  url: string
  naturalWidth: number
  naturalHeight: number
  initialCrop: CropRect | null
}>()
const emit = defineEmits<{
  crop: [CropRect]
  confirm: []
  cancel: []
}>()

const imgRef = ref<HTMLImageElement>()

const dragging = ref(false)
const start = reactive({ x: 0, y: 0 })
// 当前矩形（原图像素坐标）
const rect = reactive<CropRect>({ x: 0, y: 0, width: 0, height: 0 })
let throttleTimer: ReturnType<typeof setTimeout> | null = null

watch(visible, (v) => {
  if (v) {
    if (props.initialCrop) {
      Object.assign(rect, props.initialCrop)
    } else {
      Object.assign(rect, { x: 0, y: 0, width: 0, height: 0 })
    }
  }
})

// 视觉矩形定位：原图像素坐标 → 相对图片容器的百分比
const rectStyle = computed(() => ({
  left: `${(rect.x / props.naturalWidth) * 100}%`,
  top: `${(rect.y / props.naturalHeight) * 100}%`,
  width: `${(rect.width / props.naturalWidth) * 100}%`,
  height: `${(rect.height / props.naturalHeight) * 100}%`,
}))

function toOriginal(clientX: number, clientY: number): { x: number; y: number } {
  const img = imgRef.value
  if (!img) return { x: 0, y: 0 }
  const r = img.getBoundingClientRect()
  const sx = props.naturalWidth / r.width
  const sy = props.naturalHeight / r.height
  return {
    x: Math.round((clientX - r.left) * sx),
    y: Math.round((clientY - r.top) * sy),
  }
}

function emitCropThrottled() {
  if (throttleTimer) return
  throttleTimer = setTimeout(() => {
    throttleTimer = null
    emit('crop', { ...rect })
  }, 50)
}

function onPointerDown(e: PointerEvent) {
  dragging.value = true
  const p = toOriginal(e.clientX, e.clientY)
  start.x = p.x
  start.y = p.y
  Object.assign(rect, { x: p.x, y: p.y, width: 0, height: 0 })
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return
  const p = toOriginal(e.clientX, e.clientY)
  rect.x = Math.max(0, Math.min(start.x, p.x))
  rect.y = Math.max(0, Math.min(start.y, p.y))
  rect.width = Math.abs(p.x - start.x)
  rect.height = Math.abs(p.y - start.y)
  emitCropThrottled()
}

function onPointerUp() {
  if (!dragging.value) return
  dragging.value = false
  if (throttleTimer) {
    clearTimeout(throttleTimer)
    throttleTimer = null
  }
  emit('crop', { ...rect })
}
</script>

<template>
  <el-dialog v-model="visible" title="裁剪图片" width="680px" append-to-body @closed="emit('confirm')">
    <div class="crop-container" @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp">
      <img ref="imgRef" :src="url" class="crop-img" draggable="false" />
      <div class="crop-rect" :style="rectStyle"></div>
    </div>

    <template #footer>
      <el-button @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.crop-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f7f8fb;
  border-radius: var(--app-radius-md);
  user-select: none;
  cursor: crosshair;
  overflow: hidden;
}

.crop-img {
  display: block;
  max-width: 100%;
  max-height: 60vh;
}

.crop-rect {
  position: absolute;
  border: 2px solid var(--app-primary);
  background: rgba(236, 114, 150, 0.15);
  pointer-events: none;
}
</style>
