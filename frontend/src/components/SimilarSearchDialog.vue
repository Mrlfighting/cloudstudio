<script setup lang="ts">
/**
 * 通用以图搜图弹窗：对平台已有图片搜相似（公共图库 / 空间），跨详情页复用
 */
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { pictureApi } from '@/api/picture'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { SearchResult } from '@/types/search'
import SimilarResultCard from './SimilarResultCard.vue'

const props = defineProps<{
  pictureId: number
  kind: 'picture' | 'space'
}>()

const visible = defineModel<boolean>({ default: false })

const loading = ref(false)
const rows = ref<SearchResult[]>([])
const warnings = ref<string[]>([])

async function search() {
  if (!props.pictureId) return
  loading.value = true
  rows.value = []
  warnings.value = []
  try {
    const res =
      props.kind === 'picture'
        ? await pictureApi.similar(props.pictureId)
        : await spaceApi.similar(props.pictureId)
    rows.value = res.sources.flatMap((s) => s.results)
    warnings.value = res.sources
      .filter((s) => s.error || s.skipped)
      .map((s) => (s.error ? `「${s.source_name}」失败：${s.error}` : `「${s.source_name}」未启用`))
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '以图搜图失败'))
  } finally {
    loading.value = false
  }
}

watch(visible, (v) => {
  if (v) search()
})
</script>

<template>
  <el-dialog v-model="visible" title="以图搜图" width="720px">
    <el-alert
      v-for="(w, i) in warnings"
      :key="i"
      :title="w"
      type="warning"
      :closable="false"
      class="warn-item"
    />

    <div v-loading="loading" class="grid">
      <SimilarResultCard v-for="(item, i) in rows" :key="i" :item="item" />
    </div>

    <el-empty v-if="!loading && rows.length === 0" description="未找到相似图片" />
  </el-dialog>
</template>

<style scoped>
.warn-item {
  margin-bottom: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  min-height: 120px;
}
</style>
