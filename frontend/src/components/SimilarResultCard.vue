<script setup lang="ts">
/**
 * 外部相似图片卡片：以图搜图结果项（缩略图 + 来源网站 + 标题，点击跳转来源页）
 */
import type { SearchResult } from '@/types/search'
import EmptyValue from './EmptyValue.vue'

const props = defineProps<{
  item: SearchResult
}>()

function openSource() {
  window.open(props.item.source_url, '_blank', 'noopener')
}
</script>

<template>
  <el-card class="sim-card" shadow="hover" :body-style="{ padding: '0' }">
    <a
      class="thumb-link"
      :href="item.source_url"
      target="_blank"
      rel="noopener"
      @click.prevent="openSource"
    >
      <el-image class="thumb" :src="item.thumbnail_url" fit="cover" lazy>
        <template #error>
          <div class="img-error">
            <el-icon><Picture /></el-icon>
            <span>加载失败</span>
          </div>
        </template>
      </el-image>
    </a>

    <div class="body">
      <div class="meta">
        <el-tag size="small" type="success" effect="plain">{{ item.source_name }}</el-tag>
        <span v-if="item.score !== null" class="score">相似 {{ (item.score * 100).toFixed(0) }}%</span>
      </div>
      <div class="title"><EmptyValue :value="item.title" placeholder="无标题" /></div>
    </div>
  </el-card>
</template>

<style scoped>
.sim-card {
  border-radius: var(--app-radius-md) !important;
  overflow: hidden;
  transition: transform .2s, box-shadow .2s;
}

.sim-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--app-shadow-soft) !important;
}

.thumb-link {
  display: block;
  height: 180px;
  overflow: hidden;
  background: #f7f8fb;
}

.thumb {
  width: 100%;
  height: 100%;
  display: block;
}

.img-error {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #a8abb2;
  font-size: 13px;
}

.body {
  padding: 12px 14px;
}

.meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.score {
  font-size: 12px;
  color: var(--app-muted);
}

.title {
  margin-top: 8px;
  font-size: 14px;
  color: var(--app-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
