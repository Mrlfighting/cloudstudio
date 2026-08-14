<script setup lang="ts">
/**
 * 用户端图片列表：搜索 / 分类 / 排序 / 分页
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { pictureApi } from '@/api/picture'
import { getErrorMessage } from '@/api/http'
import { PICTURE_CATEGORIES, type PictureListItemRead, type PictureSort } from '@/types/picture'
import PictureCard from '@/components/PictureCard.vue'

const loading = ref(false)
const rows = ref<PictureListItemRead[]>([])

const filters = reactive({
  keyword: '',
  category: '',
  sort: 'time' as PictureSort,
})

const pagination = reactive({
  page: 1,
  itemsPerPage: 20,
  total: 0,
})

async function load() {
  loading.value = true
  try {
    const res = await pictureApi.list({
      page: pagination.page,
      items_per_page: pagination.itemsPerPage,
      category: filters.category || undefined,
      keyword: filters.keyword || undefined,
      sort: filters.sort,
    })
    rows.value = res.data
    pagination.total = res.total_count
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取图片列表失败'))
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  pagination.page = 1
  load()
}

function onPageChange() {
  load()
}

function onSizeChange() {
  pagination.page = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">图片库</h2>

    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索名称/简介/标签"
          clearable
          class="search"
          @keyup.enter="resetAndLoad"
          @clear="resetAndLoad"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <el-select
          v-model="filters.category"
          placeholder="全部分类"
          clearable
          class="category"
          @change="resetAndLoad"
        >
          <el-option v-for="c in PICTURE_CATEGORIES" :key="c" :label="c" :value="c" />
        </el-select>

        <el-radio-group v-model="filters.sort" @change="resetAndLoad">
          <el-radio-button value="time">最新</el-radio-button>
          <el-radio-button value="popularity">最热</el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <div v-loading="loading" class="grid">
      <PictureCard v-for="item in rows" :key="item.id" :item="item" />
    </div>

    <el-empty v-if="!loading && rows.length === 0" description="暂无图片" />

    <div v-if="pagination.total > 0" class="pagination-wrap">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.itemsPerPage"
        :total="pagination.total"
        :page-sizes="[20, 40, 60]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar-card {
  border-radius: 10px;
  margin-bottom: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search {
  width: 280px;
}

.category {
  width: 160px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
