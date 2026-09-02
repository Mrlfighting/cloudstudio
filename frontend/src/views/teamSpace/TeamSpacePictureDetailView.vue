<script setup lang="ts">
/**
 * 团队空间图片详情：大图 + 元信息 + 编辑/删除 + 协同编辑（缩放/旋转/裁剪实时同步）。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { useTeamStore } from '@/stores/team'
import { useAuthStore } from '@/stores/auth'
import type { CropRect, PersistedEditState, PictureEditState, PictureRead } from '@/types/picture'
import EmptyValue from '@/components/EmptyValue.vue'
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

async function load() {
  loading.value = true
  try {
    detail.value = await teamSpaceApi.getPicture(spaceId.value, pictureId.value)
    // 用落库的 edit_state 初始化视图（缩放默认 1.0，不落库）
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
    <el-result v-if="!team.loading && !team.isMember" icon="warning" title="无访问权限" sub-title="你不是该团队成员">
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/team')">返回团队列表</el-button>
      </template>
    </el-result>

    <template v-else>
      <el-skeleton v-if="loading" :rows="8" animated />

      <el-result v-else-if="notFound || !detail" icon="warning" title="图片不存在" sub-title="该图片可能已被删除">
        <template #extra>
          <el-button type="primary" @click="router.push(`/spaces/team/${spaceId}`)">返回团队空间</el-button>
        </template>
      </el-result>

      <template v-else>
        <div class="detail-layout">
          <div class="image-panel">
            <img class="main-img" :src="detail.url" alt="" :style="imgStyle" />
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

          <el-card class="info-panel" shadow="never">
            <template #header>
              <div class="info-header">
                <span>{{ detail.name }}</span>
                <div class="actions">
                  <el-button :icon="'Share'" @click="shareVisible = true">分享</el-button>
                  <el-button v-if="team.canWrite" type="primary" @click="editVisible = true">编辑</el-button>
                  <el-button v-if="team.canDelete" type="danger" @click="onDelete">删除</el-button>
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
                  <el-tag v-for="t in detail.tags" :key="t" size="small" effect="plain" type="primary">{{ t }}</el-tag>
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
              <el-descriptions-item label="上传者 ID">{{ detail.user_id }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">
                <EmptyValue :value="detail.created_at" />
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
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

<style scoped>
.detail-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 20px;
  align-items: start;
}

.image-panel {
  position: relative;
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.main-img {
  max-width: 100%;
  max-height: 70vh;
  display: block;
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
