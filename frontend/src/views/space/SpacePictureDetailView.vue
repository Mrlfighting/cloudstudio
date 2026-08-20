<script setup lang="ts">
/**
 * 空间图片详情：大图 + 元信息 + 编辑/删除（空间图片私有，不提供下载）
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { PictureRead } from '@/types/picture'
import EmptyValue from '@/components/EmptyValue.vue'
import SimilarSearchDialog from '@/components/SimilarSearchDialog.vue'
import SpacePictureEditDialog from './SpacePictureEditDialog.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const notFound = ref(false)
const detail = ref<PictureRead | null>(null)
const editVisible = ref(false)
const similarVisible = ref(false)

const id = computed(() => Number(route.params.id))

function formatSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '未知'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

async function load() {
  loading.value = true
  try {
    detail.value = await spaceApi.getPicture(id.value)
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
}

async function onDelete() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm(`确认删除图片「${detail.value.name}」？此操作不可撤销`, '删除图片', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await spaceApi.removePicture(detail.value.id)
    ElMessage.success('图片已删除')
    router.push('/spaces/gallery')
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '删除失败'))
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <el-skeleton v-if="loading" :rows="8" animated />

    <el-result
      v-else-if="notFound || !detail"
      icon="warning"
      title="图片不存在"
      sub-title="该图片可能已被删除"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/gallery')">返回空间图册</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="detail-layout">
        <div class="image-panel">
          <el-image
            class="main-img"
            :src="detail.url"
            fit="contain"
            :preview-src-list="[detail.url]"
            preview-teleported
          />
        </div>

        <el-card class="info-panel" shadow="never">
          <template #header>
            <div class="info-header">
              <span>{{ detail.name }}</span>
              <div class="actions">
                <el-button :icon="'Search'" @click="similarVisible = true">搜相似图</el-button>
                <el-button type="primary" @click="editVisible = true">编辑</el-button>
                <el-button type="danger" @click="onDelete">删除</el-button>
              </div>
            </div>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="分类">
              <el-tag v-if="detail.category" size="small" type="info">{{ detail.category }}</el-tag>
              <EmptyValue v-else />
            </el-descriptions-item>
            <el-descriptions-item label="标签">
              <template v-if="detail.tags.length">
                <el-tag v-for="t in detail.tags" :key="t" size="small" effect="plain" type="primary">
                  {{ t }}
                </el-tag>
              </template>
              <EmptyValue v-else />
            </el-descriptions-item>
            <el-descriptions-item label="简介">
              <EmptyValue :value="detail.introduction" />
            </el-descriptions-item>
            <el-descriptions-item label="尺寸">
              <EmptyValue
                :value="detail.pic_width && detail.pic_height ? `${detail.pic_width} × ${detail.pic_height}` : null"
              />
            </el-descriptions-item>
            <el-descriptions-item label="格式">
              <EmptyValue :value="detail.pic_format" />
            </el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatSize(detail.pic_size) }}</el-descriptions-item>
            <el-descriptions-item label="色彩模式">
              <EmptyValue :value="detail.color_mode" />
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              <EmptyValue :value="detail.created_at" />
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </div>
    </template>

    <SpacePictureEditDialog v-model="editVisible" :picture="detail" @success="load" />
    <SimilarSearchDialog v-model="similarVisible" :picture-id="detail?.id ?? 0" kind="space" />
  </div>
</template>

<style scoped>
.detail-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 20px;
  align-items: start;
}

.image-panel {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.main-img {
  width: 100%;
  max-height: 70vh;
}

.info-panel {
  border-radius: 10px;
}

.info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 18px;
  font-weight: 600;
  gap: 8px;
}

.actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 900px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
