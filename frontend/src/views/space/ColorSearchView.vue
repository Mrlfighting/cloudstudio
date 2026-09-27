<script setup lang="ts">
/**
 * 私有空间颜色搜图：选择目标颜色，按主色调距离查找自己的空间图片。
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { ColorSearchItem, SpaceInfoRead } from '@/types/space'
import PictureCard from '@/components/PictureCard.vue'
import PageIntro from '@/components/PageIntro.vue'

const router = useRouter()

const loading = ref(true)
const searching = ref(false)
const notFound = ref(false)
const loadError = ref('')
const searched = ref(false)
const color = ref('#409eff')
const space = ref<SpaceInfoRead | null>(null)
const rows = ref<ColorSearchItem[]>([])

async function loadSpace() {
  loading.value = true
  notFound.value = false
  loadError.value = ''
  try {
    space.value = await spaceApi.getMy()
  } catch (err) {
    space.value = null
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      notFound.value = true
    } else {
      loadError.value = getErrorMessage(err, '获取私有空间失败')
    }
  } finally {
    loading.value = false
  }
}

async function search() {
  if (!space.value || !color.value) return

  searching.value = true
  searched.value = false
  try {
    const result = await spaceApi.searchByColor({ color: color.value, limit: 50 })
    rows.value = [...result].sort((a, b) => a.color_distance - b.color_distance)
    searched.value = true
  } catch (err) {
    rows.value = []
    ElMessage.error(getErrorMessage(err, '按颜色搜索失败'))
  } finally {
    searching.value = false
  }
}

function formatDistance(distance: number): string {
  return Number.isInteger(distance) ? String(distance) : distance.toFixed(2)
}

onMounted(loadSpace)
</script>

<template>
  <div class="page-container">
    <div class="page-head">
      <PageIntro
        eyebrow="COLOR SEARCH · 颜色搜图"
        title="按颜色寻找图片"
        subtitle="从你的私有空间中查找主色调最接近的图片"
      />
      <div class="page-actions">
        <el-button @click="router.push('/spaces')">返回我的空间</el-button>
        <el-button @click="router.push('/spaces/gallery')">查看空间图册</el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />

    <el-result
      v-else-if="notFound"
      icon="info"
      title="你还没有创建私有空间"
      sub-title="颜色搜图只检索你的私有空间图片，创建空间并上传图片后即可使用"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces/create')">创建私有空间</el-button>
      </template>
    </el-result>

    <el-result
      v-else-if="loadError"
      icon="error"
      title="无法加载私有空间"
      :sub-title="loadError"
    >
      <template #extra>
        <el-button type="primary" @click="loadSpace">重新加载</el-button>
      </template>
    </el-result>

    <template v-else-if="space">
      <el-card class="search-card" shadow="never">
        <div class="search-copy">
          <div class="space-name">搜索空间：{{ space.name }}</div>
          <div class="search-hint">选择颜色后，结果会按主色调距离从近到远排列，最多显示 50 张。</div>
        </div>
        <div class="search-controls">
          <el-color-picker v-model="color" size="large" />
          <el-input v-model="color" class="color-input" maxlength="7" aria-label="目标颜色" />
          <el-button type="primary" :icon="'Search'" :loading="searching" @click="search">
            搜索相近图片
          </el-button>
        </div>
      </el-card>

      <div v-loading="searching" class="results">
        <div v-for="item in rows" :key="item.id" class="color-item">
          <PictureCard :item="item" kind="space" />
          <el-tag class="distance" size="small" type="info" effect="dark">
            距离 {{ formatDistance(item.color_distance) }}
          </el-tag>
        </div>
      </div>

      <el-empty
        v-if="!searching && searched && rows.length === 0"
        description="没有找到包含主色信息的相近图片"
      />

      <el-empty
        v-else-if="!searching && !searched"
        description="选择一个颜色，开始搜索你的空间图片"
      />
    </template>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
}

.search-card {
  margin-bottom: 24px;
  border-radius: var(--app-radius-lg) !important;
}

.search-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.space-name {
  color: var(--app-ink);
  font-size: 16px;
  font-weight: 800;
}

.search-hint {
  margin-top: 6px;
  color: var(--app-muted);
  font-size: 13px;
}

.search-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.color-input {
  width: 110px;
}

.results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
  min-height: 120px;
}

.color-item {
  position: relative;
  min-width: 0;
}

.distance {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
}

@media (max-width: 760px) {
  .page-head,
  .search-card :deep(.el-card__body) {
    flex-direction: column;
  }

  .page-actions,
  .search-controls {
    width: 100%;
    flex-wrap: wrap;
  }

  .search-controls .el-button {
    flex: 1;
  }
}
</style>
