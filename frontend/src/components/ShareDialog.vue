<script setup lang="ts">
/**
 * 分享弹窗：展示图片链接 + 复制按钮 + 二维码（纯前端）
 */
import { ElMessage } from 'element-plus'
import QrcodeVue from 'qrcode.vue'

const props = defineProps<{
  url: string
}>()

const visible = defineModel<boolean>({ default: false })

async function copyLink() {
  try {
    await navigator.clipboard.writeText(props.url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="分享图片" width="420px" append-to-body>
    <div class="share-body">
      <qrcode-vue :value="url" :size="200" level="M" class="qr" />
      <div class="link-row">
        <el-input :model-value="url" readonly />
        <el-button type="primary" @click="copyLink">复制链接</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.share-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.qr {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 8px;
}

.link-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
</style>
