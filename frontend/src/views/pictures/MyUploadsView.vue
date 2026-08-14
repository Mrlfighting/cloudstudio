<script setup lang="ts">
/**
 * 我的上传：登录用户查看自己上传的全部图片（含审核状态与拒绝理由）
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { pictureApi } from '@/api/picture'
import { getErrorMessage } from '@/api/http'
import type { PictureListItemRead } from '@/types/picture'
import EmptyValue from '@/components/EmptyValue.vue'

const loading = ref(false)
const rows = ref<PictureListItemRead[]>([])

const filters = reactive({
  status: '' as '' | 'pending' | 'approved' | 'rejected',
})

const pagination = reactive({
  page: 1,
  itemsPerPage: 10,
  total: 0,
})

async function load() {
  loading.value = true
  try {
    const res = await pictureApi.my({
      page: pagination.page,
      items_per_page: pagination.itemsPerPage,
      status: filters.status || undefined,
    })
    rows.value = res.data
    pagination.total = res.total_count
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取我的上传失败'))
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  pagination.page = 1
  load()
}

function statusTagType(s: string): 'success' | 'warning' | 'danger' | 'info' {
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'danger'
  if (s === 'pending') return 'warning'
  return 'info'
}

function statusLabel(s: string): string {
  return { pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] ?? s
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">我的上传</h2>

    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <el-select
          v-model="filters.status"
          placeholder="全部状态"
          clearable
          class="status"
          @change="resetAndLoad"
        >
          <el-option label="待审核" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>
      </div>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column label="缩略图" width="90">
          <template #default="{ row }">
            <el-image
              :src="row.url"
              fit="cover"
              class="thumb"
              :preview-src-list="[row.url]"
              preview-teleported
            />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <EmptyValue :value="row.category" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审核理由" min-width="180">
          <template #default="{ row }">
            <EmptyValue :value="row.review_reason" />
          </template>
        </el-table-column>
        <el-table-column prop="download_count" label="下载" width="70" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <EmptyValue :value="row.created_at" />
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && rows.length === 0" description="还没有上传过图片" />

      <div v-if="pagination.total > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.itemsPerPage"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="load"
          @size-change="resetAndLoad"
        />
      </div>
    </el-card>
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
  gap: 12px;
}

.status {
  width: 140px;
}

.table-card {
  border-radius: 10px;
}

.thumb {
  width: 60px;
  height: 45px;
  border-radius: 4px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
