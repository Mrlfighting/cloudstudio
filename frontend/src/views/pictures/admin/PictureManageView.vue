<script setup lang="ts">
/**
 * 管理员图片管理：全状态列表 + 状态过滤 + 上传/审核/编辑/删除
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { pictureApi } from '@/api/picture'
import { getErrorMessage } from '@/api/http'
import {
  PICTURE_CATEGORIES,
  type PictureListItemRead,
  type PictureSort,
  type PictureStatus,
} from '@/types/picture'
import PictureUploadDialog from './PictureUploadDialog.vue'
import PictureEditDialog from './PictureEditDialog.vue'
import EmptyValue from '@/components/EmptyValue.vue'

const loading = ref(false)
const rows = ref<PictureListItemRead[]>([])

const filters = reactive({
  keyword: '',
  category: '',
  sort: 'time' as PictureSort,
  status: '' as PictureStatus | '',
})

const pagination = reactive({
  page: 1,
  itemsPerPage: 10,
  total: 0,
})

const uploadVisible = ref(false)
const editVisible = ref(false)
const editing = ref<PictureListItemRead | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await pictureApi.manage({
      page: pagination.page,
      items_per_page: pagination.itemsPerPage,
      category: filters.category || undefined,
      keyword: filters.keyword || undefined,
      sort: filters.sort,
      status: filters.status || undefined,
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

function statusTagType(s: string): 'success' | 'warning' | 'danger' | 'info' {
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'danger'
  if (s === 'pending') return 'warning'
  return 'info'
}

function statusLabel(s: string): string {
  return { pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] ?? s
}

async function onAudit(row: PictureListItemRead, status: 'approved' | 'rejected') {
  const action = status === 'approved' ? '通过' : '拒绝'
  let reviewReason: string | undefined

  if (status === 'rejected') {
    // 拒绝必须填写理由
    try {
      const { value } = await ElMessageBox.prompt(
        `请输入拒绝「${row.name}」的理由`,
        '拒绝图片',
        {
          type: 'warning',
          confirmButtonText: '确认拒绝',
          cancelButtonText: '取消',
          inputPattern: /\S+/,
          inputErrorMessage: '拒绝理由不能为空',
        },
      )
      reviewReason = value.trim()
    } catch {
      return // 取消
    }
  } else {
    try {
      await ElMessageBox.confirm(`确认通过图片「${row.name}」？`, '审核图片', {
        type: 'warning',
        confirmButtonText: '确认',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
  }

  try {
    await pictureApi.audit(row.id, status, reviewReason)
    ElMessage.success(`图片审核${action}`)
    load()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '审核失败'))
  }
}

function openEdit(row: PictureListItemRead) {
  editing.value = row
  editVisible.value = true
}

async function onDelete(row: PictureListItemRead) {
  try {
    await ElMessageBox.confirm(`确认删除图片「${row.name}」？此操作不可撤销`, '删除图片', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await pictureApi.remove(row.id)
    ElMessage.success('图片已删除')
    load()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '删除失败'))
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">图片管理</h2>

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

        <el-select
          v-model="filters.category"
          placeholder="全部分类"
          clearable
          class="category"
          @change="resetAndLoad"
        >
          <el-option v-for="c in PICTURE_CATEGORIES" :key="c" :label="c" :value="c" />
        </el-select>

        <el-input
          v-model="filters.keyword"
          placeholder="搜索名称/标签"
          clearable
          class="search"
          @keyup.enter="resetAndLoad"
          @clear="resetAndLoad"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <el-radio-group v-model="filters.sort" @change="resetAndLoad">
          <el-radio-button value="time">最新</el-radio-button>
          <el-radio-button value="popularity">最热</el-radio-button>
        </el-radio-group>

        <el-button type="primary" :icon="'Upload'" class="upload-btn" @click="uploadVisible = true">
          上传图片
        </el-button>
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
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <EmptyValue :value="row.category" />
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="140">
          <template #default="{ row }">
            <template v-if="row.tags.length">
              <el-tag v-for="t in row.tags.slice(0, 3)" :key="t" size="small" effect="plain" type="primary">
                {{ t }}
              </el-tag>
            </template>
            <EmptyValue v-else />
          </template>
        </el-table-column>
        <el-table-column label="尺寸/格式" width="130">
          <template #default="{ row }">
            <template v-if="row.pic_width && row.pic_height">
              {{ row.pic_width }}×{{ row.pic_height }}<br />
              <span class="muted">{{ row.pic_format }}</span>
            </template>
            <EmptyValue v-else />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审核理由" min-width="140">
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
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button link type="success" @click="onAudit(row, 'approved')">通过</el-button>
              <el-button link type="danger" @click="onAudit(row, 'rejected')">拒绝</el-button>
            </template>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.itemsPerPage"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>

    <PictureUploadDialog v-model="uploadVisible" @success="load" />
    <PictureEditDialog v-model="editVisible" :picture="editing" @success="load" />
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
  flex-wrap: wrap;
}

.status {
  width: 130px;
}

.category {
  width: 140px;
}

.search {
  width: 220px;
}

.upload-btn {
  margin-left: auto;
}

.table-card {
  border-radius: 10px;
}

.thumb {
  width: 60px;
  height: 45px;
  border-radius: 4px;
}

.muted {
  color: #909399;
  font-size: 12px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
