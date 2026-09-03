<script setup lang="ts">
/**
 * 团队空间图片详情：大图 + 信息卡 + 协同编辑工具条
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { useTeamStore } from '@/stores/team'
import { useAuthStore } from '@/stores/auth'
import type { CropRect, PersistedEditState, PictureEditState, PictureRead } from '@/types/picture'
import ShareDialog from '@/components/ShareDialog.vue'
import PictureEditDialog from '@/components/PictureEditDialog.vue'
import CollabToolbar from '@/components/CollabToolbar.vue'
import CollabCropOverlay from '@/components/CollabCropOverlay.vue'
import { useCollabSocket } from '@/composables/useCollabSocket'

const route = useRoute()
const router = useRouter()
const team = useTeamStore()
const auth = useAuthStore()

const spaceId = computed(() => Number(route.params.id))
const pictureId = computed(() => Number(route.params.pictureId))
type DetailTextRow = { label: string; type: 'text'; value: string }
type DetailChipRow = { label: string; type: 'chips'; chips: string[] }
type DetailRow = DetailTextRow | DetailChipRow
type DetailStat = { label: string; value: string }

const loading = ref(false)
const notFound = ref(false)
const detail = ref<PictureRead | null>(null)
const editVisible = ref(false)
const shareVisible = ref(false)
const cropVisible = ref(false)

const {
  editState,
  editorUser,
  isEditing,
  connect,
  disconnect,
  enterEdit,
  exitEdit,
  zoomIn,
  zoomOut,
  rotateLeft,
  rotateRight,
  crop: applyCrop,
  save: saveEdit,
} = useCollabSocket(spaceId.value, pictureId.value, auth.user?.id ?? 0, { rotation: 0, zoom: 1.0, crop: null })

function normalizeSaved(es: PersistedEditState | null): PictureEditState {
  return { rotation: es?.rotation ?? 0, zoom: 1.0, crop: es?.crop ?? null }
}

function cropClipPath(crop: CropRect, w: number, h: number): string {
  const top = (crop.y / h) * 100
  const right = ((w - crop.x - crop.width) / w) * 100
  const bottom = ((h - crop.y - crop.height) / h) * 100
  const left = (crop.x / w) * 100
  return `inset(${top}% ${right}% ${bottom}% ${left}%)`
}

const imgStyle = computed(() => {
  const s = editState.value
  const w = detail.value?.pic_width
  const h = detail.value?.pic_height
  return {
    transform: `rotate(${s.rotation}deg) scale(${s.zoom})`,
    clipPath: s.crop && w && h ? cropClipPath(s.crop, w, h) : 'none',
    transition: 'transform 0.15s ease',
  }
})

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
    { label: '上传者 ID', type: 'text', value: String(detail.value.user_id) },
    { label: '创建时间', type: 'text', value: formatDateTime(detail.value.created_at) },
  ]
})

async function load() {
  loading.value = true
  try {
    detail.value = await teamSpaceApi.getPicture(spaceId.value, pictureId.value)
    editState.value = normalizeSaved(detail.value.edit_state)
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
    await teamSpaceApi.removePicture(spaceId.value, detail.value.id)
    ElMessage.success('图片已删除')
    router.push(`/spaces/team/${spaceId.value}`)
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '删除失败'))
  }
}

function onCrop(rect: CropRect) {
  applyCrop(rect)
}

onMounted(async () => {
  await team.load(spaceId.value)
  await load()
  if (team.canWrite) connect()
})

onBeforeUnmount(() => {
  disconnect()
})
</script>

<template>
  <div class="page-container">
    <el-result
      v-if="!team.loading && !team.isMember"
      icon="warning"
      title="无访问权限"
      sub-title="你不是该团队成员"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/team')">返回团队列表</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="detail-topbar">
        <div class="page-intro">
          <div class="eyebrow">DETAIL PAGE</div>
          <h2 class="page-title">图片详情页</h2>
          <p class="page-subtitle">团队图片页保留协同编辑能力，同时把主预览、信息表和操作区整理得更完整。</p>
        </div>

        <div class="detail-nav-pills">
          <span class="detail-nav-pill">团队空间</span>
          <span class="detail-nav-pill is-active">详情页</span>
          <span class="detail-nav-pill">公共图库</span>
          <span class="detail-nav-pill">个人空间</span>
        </div>
      </div>

      <el-skeleton v-if="loading" :rows="8" animated />

      <el-result v-else-if="notFound || !detail" icon="warning" title="图片不存在" sub-title="该图片可能已被删除">
        <template #extra>
          <el-button type="primary" @click="router.push(`/spaces/team/${spaceId}`)">返回团队空间</el-button>
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

                <img class="detail-image" :src="detail.url" alt="" :style="imgStyle" />

                <CollabToolbar
                  v-if="team.canWrite"
                  :is-editing="isEditing"
                  :editor-user="editorUser"
                  @enter="enterEdit"
                  @exit="exitEdit"
                  @zoom-in="zoomIn"
                  @zoom-out="zoomOut"
                  @rotate-left="rotateLeft"
                  @rotate-right="rotateRight"
                  @crop="cropVisible = true"
                  @save="saveEdit"
                />
              </div>

              <div class="detail-section">
                <div class="detail-section-head">
                  <div>
                    <h3 class="detail-title">{{ detail.name }}</h3>
                    <p class="detail-desc">{{ detail.introduction || '暂无简介，团队素材可在右侧查看完整属性。' }}</p>
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
                    <div class="detail-side-note">{{ team.canWrite ? '协同编辑中可直接修改' : '仅查看模式' }}</div>
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
                    <div class="detail-side-note">分享、编辑、删除</div>
                  </div>
                </div>
              </template>

              <div class="detail-action-list">
                <el-button type="primary" @click="editVisible = true">
                  <el-icon><Edit /></el-icon>
                  编辑图片
                </el-button>
                <el-button @click="shareVisible = true">
                  <el-icon><Share /></el-icon>
                  分享素材
                </el-button>
                <el-button v-if="team.canDelete" type="danger" @click="onDelete">
                  <el-icon><Delete /></el-icon>
                  删除图片
                </el-button>
              </div>
            </el-card>
          </div>
        </div>
      </template>
    </template>

    <ShareDialog v-model="shareVisible" :url="detail?.url ?? ''" />
    <PictureEditDialog v-model="editVisible" :picture="detail" kind="team" :space-id="spaceId" @success="load" />
    <CollabCropOverlay
      v-if="team.canWrite"
      v-model="cropVisible"
      :url="detail?.url ?? ''"
      :natural-width="detail?.pic_width ?? 1"
      :natural-height="detail?.pic_height ?? 1"
      :initial-crop="editState.crop"
      @crop="onCrop"
    />
  </div>
</template>
