<script setup lang="ts">
/**
 * 颜色搜图弹窗：选颜色搜索空间内主色调相近的图片（按距离升序）
 */
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { ColorSearchItem } from '@/types/space'
import PictureCard from '@/components/PictureCard.vue'

const visible = defineModel<boolean>({ default: false })

const color = ref('#409eff')
const loading = ref(false)
const searched = ref(false)
const rows = ref<ColorSearchItem[]>([])

async function search() {
  loading.value = true
  try {
    rows.value = await spaceApi.searchByColor({ color: color.value, limit: 50 })
    searched.value = true
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '按颜色搜索失败'))
  } finally {
    loading.value = false
  }
}

watch(visible, (v) => {
  if (!v) {
    rows.value = []
    searched.value = false
  }
})
</script>

<template>
  <el-dialog v-model="visible" title="按颜色搜索" width="720px">
    <div class="picker-row">
      <el-color-picker v-model="color" />
      <el-button type="primary" :icon="'Search'" :loading="loading" @click="search">搜索</el-button>
      <span class="hint">选择颜色后，在空间内按主色调距离升序查找</span>
    </div>

    <div v-loading="loading" class="grid">
      <div v-for="item in rows" :key="item.id" class="color-item">
        <PictureCard :item="item" kind="space" />
        <el-tag class="distance" size="small" type="info" effect="plain">距离 {{ item.color_distance }}</el-tag>
      </div>
    </div>

    <el-empty v-if="!loading && searched && rows.length === 0" description="没有相近颜色的图片" />
  </el-dialog>
</template>

<style scoped>
.picker-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.hint {
  font-size: 12px;
  color: #909399;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.color-item {
  position: relative;
}

.distance {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 1;
}
</style>
