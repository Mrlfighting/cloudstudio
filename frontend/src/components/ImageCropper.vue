<script setup lang="ts">
/**
 * 图片裁剪编辑器：缩放 / 比例 / 重置 / 遮罩预览 / 确认裁剪（纯前端，基于 Cropper.js）
 */
import { onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'

const props = defineProps<{
  file: File
}>()

const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{
  confirm: [blob: Blob]
}>()

const imgRef = ref<HTMLImageElement>()
let cropper: Cropper | null = null
let objectUrl: string | null = null

const aspectRatio = ref('free')

const ratios = [
  { label: '自由', value: 'free' },
  { label: '1:1', value: '1:1' },
  { label: '4:3', value: '4:3' },
  { label: '16:9', value: '16:9' },
]

function ratioValue(ratio: string): number {
  switch (ratio) {
    case '1:1':
      return 1
    case '4:3':
      return 4 / 3
    case '16:9':
      return 16 / 9
    default:
      return NaN
  }
}

function initCropper() {
  const img = imgRef.value
  if (!img) return
  objectUrl = URL.createObjectURL(props.file)
  img.onload = () => {
    cropper = new Cropper(img, {
      aspectRatio: NaN,
      viewMode: 1,
      autoCropArea: 1,
      dragMode: 'move',
      responsive: true,
      background: true,
    })
  }
  img.src = objectUrl
}

function destroyCropper() {
  if (cropper) {
    cropper.destroy()
    cropper = null
  }
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
}

function zoomIn() {
  cropper?.zoom(0.1)
}

function zoomOut() {
  cropper?.zoom(-0.1)
}

function reset() {
  cropper?.reset()
}

function onRatioChange() {
  cropper?.setAspectRatio(ratioValue(aspectRatio.value))
}

function outputOptions(type: string): { mime: string; quality?: number } {
  switch (type) {
    case 'image/png':
      return { mime: 'image/png' }
    case 'image/webp':
      return { mime: 'image/webp', quality: 0.9 }
    case 'image/gif':
      // GIF 裁剪后无法保留动画，转 PNG 静态帧
      return { mime: 'image/png' }
    case 'image/jpeg':
    default:
      return { mime: 'image/jpeg', quality: 0.9 }
  }
}

function confirm() {
  if (!cropper) return
  const canvas = cropper.getCroppedCanvas()
  const { mime, quality } = outputOptions(props.file.type)
  canvas.toBlob(
    (blob) => {
      if (blob) {
        emit('confirm', blob)
        visible.value = false
      } else {
        ElMessage.error('裁剪失败')
      }
    },
    mime,
    quality,
  )
}

onBeforeUnmount(destroyCropper)
</script>

<template>
  <el-dialog
    v-model="visible"
    title="裁剪图片"
    width="720px"
    append-to-body
    @opened="initCropper"
    @closed="destroyCropper"
  >
    <div class="cropper-toolbar">
      <el-radio-group v-model="aspectRatio" @change="onRatioChange">
        <el-radio-button v-for="r in ratios" :key="r.value" :value="r.value">{{ r.label }}</el-radio-button>
      </el-radio-group>
      <div class="toolbar-actions">
        <el-button @click="zoomOut">-</el-button>
        <el-button @click="zoomIn">+</el-button>
        <el-button @click="reset">重置</el-button>
      </div>
    </div>

    <div class="cropper-container">
      <img ref="imgRef" alt="裁剪图片" />
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="confirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.cropper-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.cropper-container {
  width: 100%;
  height: 400px;
  background: #f7f8fb;
  border-radius: var(--app-radius-md);
}

.cropper-container img {
  max-width: 100%;
  display: block;
}
</style>
