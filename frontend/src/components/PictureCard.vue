<script setup lang="ts">
/**
 * 图片卡片：列表网格项（缩略图 + 名称 + 分类/标签 + 尺寸/格式/下载数）
 */
import { ref } from 'vue'
import type { PictureListItemRead } from '@/types/picture'
import ShareDialog from './ShareDialog.vue'

defineProps<{
  item: PictureListItemRead
}>()

const shareVisible = ref(false)
</script>

<template>
  <el-card class="pic-card" shadow="hover" :body-style="{ padding: '0' }">
    <router-link :to="`/pictures/${item.id}`" class="thumb-link">
      <el-image
        class="thumb"
        :src="item.url"
        fit="cover"
        lazy
        :preview-src-list="[item.url]"
        preview-teleported
      >
        <template #error>
          <div class="img-error">
            <el-icon><Picture /></el-icon>
            <span>加载失败</span>
          </div>
        </template>
      </el-image>
    </router-link>

    <div class="body">
      <router-link :to="`/pictures/${item.id}`" class="name">{{ item.name }}</router-link>

      <div class="tags">
        <el-tag v-if="item.category" size="small" type="info" effect="plain">{{ item.category }}</el-tag>
        <el-tag
          v-for="tag in item.tags.slice(0, 3)"
          :key="tag"
          size="small"
          effect="plain"
          type="primary"
        >
          {{ tag }}
        </el-tag>
      </div>

      <div class="stats">
        <span v-if="item.pic_width && item.pic_height">{{ item.pic_width }}×{{ item.pic_height }}</span>
        <span v-if="item.pic_format">{{ item.pic_format }}</span>
        <span class="dl-count"><el-icon><Download /></el-icon>{{ item.download_count }}</span>
        <button class="share-btn" title="分享" @click.stop="shareVisible = true">
          <el-icon><Share /></el-icon>
        </button>
      </div>
    </div>

    <ShareDialog v-model="shareVisible" :url="item.url" />
  </el-card>
</template>

<style scoped>
.pic-card {
  border-radius: 10px;
  overflow: hidden;
  transition: transform 0.2s;
}

.pic-card:hover {
  transform: translateY(-4px);
}

.thumb-link {
  display: block;
  height: 180px;
  overflow: hidden;
  background: #f0f2f5;
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

.name {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name:hover {
  color: #409eff;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  min-height: 22px;
}

.stats {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.dl-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.share-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #909399;
  display: inline-flex;
  align-items: center;
  padding: 0;
  font-size: 14px;
}

.share-btn:hover {
  color: #409eff;
}
</style>
