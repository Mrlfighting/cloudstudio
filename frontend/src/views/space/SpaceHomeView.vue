<script setup lang="ts">
/**
 * 我的空间首页：空间信息 + 容量/数量进度 + 操作入口；无空间时引导创建
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import { formatBytes, spaceLevelLabel, type SpaceInfoRead } from '@/types/space'
import type { PictureListItemRead } from '@/types/picture'
import PictureCard from '@/components/PictureCard.vue'
import SpaceLevelDialog from './SpaceLevelDialog.vue'

const router = useRouter()

const loading = ref(false)
const notFound = ref(false)
const space = ref<SpaceInfoRead | null>(null)
const recent = ref<PictureListItemRead[]>([])
const levelVisible = ref(false)

function capacityPercent(): number {
  if (!space.value || space.value.max_size <= 0) return 0
  return Math.min(100, Math.round((space.value.total_size / space.value.max_size) * 100))
}

function countPercent(): number {
  if (!space.value || space.value.max_count <= 0) return 0
  return Math.min(100, Math.round((space.value.total_count / space.value.max_count) * 100))
}

async function load() {
  loading.value = true
  notFound.value = false
  recent.value = []
  try {
    space.value = await spaceApi.getMy()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      notFound.value = true
    } else {
      ElMessage.error(getErrorMessage(err, '获取空间信息失败'))
    }
  } finally {
    loading.value = false
  }

  // 有空间时加载「最近上传」，失败不阻塞主页
  if (space.value) {
    try {
      const res = await spaceApi.listPictures({ page: 1, items_per_page: 8, sort: 'time' })
      recent.value = res.data
    } catch {
      recent.value = []
    }
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="hero-row">
      <div>
        <div class="eyebrow">PRIVATE SPACE · 私人工作台</div>
        <h2 class="page-title">我的空间</h2>
        <p class="page-subtitle">管理你的私藏灵感与创作资产</p>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />

    <el-result
      v-else-if="notFound"
      icon="info"
      title="你还没有创建私有空间"
      sub-title="创建一个私有空间，上传图片，与公共图库隔离存储"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/create')">创建空间</el-button>
      </template>
    </el-result>

    <el-card v-else-if="space" class="space-card" shadow="never">
      <div class="space-header">
        <div>
          <div class="space-name">
            {{ space.name }}
            <el-tag size="small" type="info" effect="plain">{{ spaceLevelLabel(space.space_level) }}</el-tag>
            <el-tag v-if="space.status === 'banned'" size="small" type="danger" effect="plain">已封禁</el-tag>
          </div>
          <div class="space-muted">空间 ID：{{ space.id }}</div>
        </div>
        <div class="space-actions">
          <el-button @click="levelVisible = true">升级 / 降级</el-button>
          <el-button type="primary" @click="router.push('/spaces/gallery')">进入空间</el-button>
        </div>
      </div>

      <el-divider />

      <div class="quota-grid">
        <div class="quota-item">
          <div class="quota-label">容量使用</div>
          <el-progress
            :percentage="capacityPercent()"
            :status="space.remaining_size < 0 ? 'exception' : undefined"
          />
          <div class="quota-text">
            {{ formatBytes(space.total_size) }} / {{ formatBytes(space.max_size) }}
            <span v-if="space.remaining_size < 0" class="over">（已超限）</span>
            <span v-else class="muted">（剩余 {{ formatBytes(space.remaining_size) }}）</span>
          </div>
        </div>

        <div class="quota-item">
          <div class="quota-label">图片数量</div>
          <el-progress
            :percentage="countPercent()"
            :status="space.remaining_count < 0 ? 'exception' : undefined"
          />
          <div class="quota-text">
            {{ space.total_count }} / {{ space.max_count }} 张
            <span v-if="space.remaining_count < 0" class="over">（已超限）</span>
            <span v-else class="muted">（剩余 {{ space.remaining_count }} 张）</span>
          </div>
        </div>
      </div>
    </el-card>

    <section v-if="space && recent.length" class="recent-section">
      <div class="recent-head">
        <h3>最近上传</h3>
        <el-button link type="primary" @click="router.push('/spaces/gallery')">查看全部</el-button>
      </div>
      <div class="masonry">
        <PictureCard v-for="item in recent" :key="item.id" :item="item" kind="space" />
      </div>
    </section>

    <SpaceLevelDialog
      v-model="levelVisible"
      :current-level="space?.space_level ?? 0"
      @success="load"
    />
  </div>
</template>

<style scoped>
.space-card {
  border-radius: var(--app-radius-lg) !important;
}

.recent-section {
  margin-top: 28px;
}

.recent-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.recent-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--app-ink);
}

.space-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.space-name {
  font-size: 24px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
}

.space-muted {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}

.space-actions {
  display: flex;
  gap: 8px;
}

.quota-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.quota-item { padding: 18px; border-radius: var(--app-radius-md); background: #fbfcfe; border: 1px solid var(--app-line-soft); }
.eyebrow { color: #b16880; font-size: 11px; font-weight: 800; letter-spacing: 2px; margin-bottom: 10px; }
.page-title { margin-bottom: 0; }
.page-subtitle { margin: 10px 0 20px; color: var(--app-muted); font-size: 15px; }

.quota-label {
  font-weight: 600;
  margin-bottom: 8px;
}

.quota-text {
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.over {
  color: #f56c6c;
}

.muted {
  color: #909399;
}

@media (max-width: 640px) {
  .quota-grid {
    grid-template-columns: 1fr;
  }
}
</style>
