<script setup lang="ts">
/**
 * 空间图片详情：大图 + 素材信息 + 编辑 / 删除 / AI 扩图
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { PictureRead } from '@/types/picture'
import OutpaintDialog from '@/components/OutpaintDialog.vue'
import SimilarSearchDialog from '@/components/SimilarSearchDialog.vue'
import ShareDialog from '@/components/ShareDialog.vue'
import PictureEditDialog from '@/components/PictureEditDialog.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const notFound = ref(false)
const detail = ref<PictureRead | null>(null)
const editVisible = ref(false)
const similarVisible = ref(false)
const shareVisible = ref(false)
const outpaintVisible = ref(false)

const id = computed(() => Number(route.params.id))
type DetailTextRow = { label: string; type: 'text'; value: string }
type DetailChipRow = { label: string; type: 'chips'; chips: string[] }
type DetailRow = DetailTextRow | DetailChipRow
type DetailStat = { label: string; value: string }

function formatSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '未知'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDateTime(value: string | null): string {
  if (!value) return '未填写'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    hour12: false,
  }).format(date)
}

function formatDimension(picWidth: number | null, picHeight: number | null): string {
  if (!picWidth || !picHeight) return '未填写'
  return `${picWidth} × ${picHeight}`
}

const previewChips = computed(() => {
  if (!detail.value) return []
  return [detail.value.category, detail.value.pic_format, formatDimension(detail.value.pic_width, detail.value.pic_height)]
    .filter((item): item is string => Boolean(item))
    .slice(0, 3)
})

const detailStats = computed<DetailStat[]>(() => {
  if (!detail.value) return []
  return [
    { label: '尺寸', value: formatDimension(detail.value.pic_width, detail.value.pic_height) },
    { label: '格式', value: detail.value.pic_format || '未填写' },
    { label: '大小', value: formatSize(detail.value.pic_size) },
    { label: '下载次数', value: String(detail.value.download_count) },
  ]
})

const detailRows = computed<DetailRow[]>(() => {
  if (!detail.value) return []
  return [
    { label: '分类', type: 'text', value: detail.value.category || '未填写' },
    { label: '标签', type: 'chips', chips: detail.value.tags },
    { label: '简介', type: 'text', value: detail.value.introduction || '未填写' },
    { label: '尺寸', type: 'text', value: formatDimension(detail.value.pic_width, detail.value.pic_height) },
    { label: '格式', type: 'text', value: detail.value.pic_format || '未填写' },
    { label: '大小', type: 'text', value: formatSize(detail.value.pic_size) },
    { label: '色彩模式', type: 'text', value: detail.value.color_mode || '未填写' },
    { label: '下载次数', type: 'text', value: String(detail.value.download_count) },
    { label: '上传者 ID', type: 'text', value: String(detail.value.user_id) },
    { label: '创建时间', type: 'text', value: formatDateTime(detail.value.created_at) },
  ]
})

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
    <div class="detail-topbar">
      <div class="page-intro">
        <div class="eyebrow">DETAIL PAGE</div>
        <h2 class="page-title">图片详情页</h2>
        <p class="page-subtitle">保留空间图片的编辑和扩图能力，同时把素材展示做得更像一张完整的详情页。</p>
      </div>

      <div class="detail-nav-pills">
        <span class="detail-nav-pill">个人空间</span>
        <span class="detail-nav-pill is-active">详情页</span>
        <span class="detail-nav-pill">公共图库</span>
        <span class="detail-nav-pill">团队空间</span>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />

    <el-result
      v-else-if="notFound || !detail"
      icon="warning"
      title="图片不存在"
      sub-title="该图片可能已被删除"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/gallery')">返回空间画廊</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="detail-grid">
        <div class="detail-stack">
          <el-card class="detail-card detail-figure-card" shadow="never">
            <div class="detail-figure">
              <div class="detail-badge">
                <el-icon><Picture /></el-icon>
                预览
              </div>

              <div class="detail-figure-tags">
                <span v-for="chip in previewChips" :key="chip" class="detail-tag-chip">{{ chip }}</span>
              </div>

              <el-image
                class="detail-image"
                :src="detail.url"
                fit="contain"
                :preview-src-list="[detail.url]"
                preview-teleported
              />
            </div>

            <div class="detail-section">
              <div class="detail-section-head">
                <div>
                  <h3 class="detail-title">{{ detail.name }}</h3>
                  <p class="detail-desc">{{ detail.introduction || '暂无简介，空间素材可在右侧查看完整属性。' }}</p>
                </div>

                <el-tag effect="plain" round type="info">图片 ID {{ detail.id }}</el-tag>
              </div>

              <div class="detail-meta-grid">
                <div v-for="stat in detailStats" :key="stat.label" class="detail-stat">
                  <span>{{ stat.label }}</span>
                  <strong>{{ stat.value }}</strong>
                </div>
              </div>
            </div>
          </el-card>
        </div>

        <div class="detail-side">
          <el-card class="detail-card detail-side-card" shadow="never">
            <template #header>
              <div class="detail-side-head">
                <div>
                  <h3 class="detail-side-title">素材信息</h3>
                  <div class="detail-side-note">空间私有素材</div>
                </div>
              </div>
            </template>

            <div class="detail-table">
              <div v-for="row in detailRows" :key="row.label" class="detail-row">
                <div class="detail-label">{{ row.label }}</div>
                <div class="detail-value">
                  <template v-if="row.type === 'chips'">
                    <div v-if="row.chips.length" class="detail-pill-list">
                      <span v-for="chip in row.chips" :key="chip" class="detail-pill">{{ chip }}</span>
                    </div>
                    <span v-else class="detail-muted">未填写</span>
                  </template>
                  <template v-else>
                    {{ row.value }}
                  </template>
                </div>
              </div>
            </div>
          </el-card>

          <el-card class="detail-card detail-side-card" shadow="never">
            <template #header>
              <div class="detail-side-head">
                <div>
                  <h3 class="detail-side-title">操作</h3>
                  <div class="detail-side-note">编辑、扩图、相似图、删除</div>
                </div>
              </div>
            </template>

            <div class="detail-action-list">
              <el-button type="primary" @click="editVisible = true">
                <el-icon><Edit /></el-icon>
                编辑图片
              </el-button>
              <el-button @click="outpaintVisible = true">
                <el-icon><MagicStick /></el-icon>
                AI 扩图
              </el-button>
              <el-button @click="similarVisible = true">
                <el-icon><Search /></el-icon>
                搜相似图
              </el-button>
              <el-button @click="shareVisible = true">
                <el-icon><Share /></el-icon>
                分享素材
              </el-button>
              <el-button type="danger" @click="onDelete">
                <el-icon><Delete /></el-icon>
                删除图片
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </template>

    <PictureEditDialog v-model="editVisible" :picture="detail" kind="space" @success="load" />
    <SimilarSearchDialog v-model="similarVisible" :picture-id="detail?.id ?? 0" kind="space" />
    <ShareDialog v-model="shareVisible" :url="detail?.url ?? ''" />
    <OutpaintDialog v-model="outpaintVisible" :picture-id="detail?.id ?? 0" :url="detail?.url ?? ''" />
  </div>
</template>
