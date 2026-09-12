<script setup lang="ts">
/**
 * 管理员空间管理：列表 + 名称/用户/级别筛选 + 详情/编辑/封禁/解封/删除
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import {
  SPACE_LEVEL_OPTIONS,
  formatBytes,
  spaceLevelLabel,
  type SpaceLevel,
  type SpaceListItemRead,
} from '@/types/space'
import EmptyValue from '@/components/EmptyValue.vue'
import SpaceDetailDialog from './SpaceDetailDialog.vue'
import SpaceEditDialog from './SpaceEditDialog.vue'

const loading = ref(false)
const rows = ref<SpaceListItemRead[]>([])

const filters = reactive({
  name: '',
  user_id: '',
  space_level: undefined as SpaceLevel | undefined,
})

const pagination = reactive({
  page: 1,
  itemsPerPage: 10,
  total: 0,
})

const detailVisible = ref(false)
const editVisible = ref(false)
const viewing = ref<SpaceListItemRead | null>(null)
const editing = ref<SpaceListItemRead | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await spaceApi.list({
      page: pagination.page,
      items_per_page: pagination.itemsPerPage,
      name: filters.name || undefined,
      user_id: filters.user_id ? Number(filters.user_id) : undefined,
      space_level: filters.space_level,
    })
    rows.value = res.data
    pagination.total = res.total_count
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取空间列表失败'))
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

function openDetail(row: SpaceListItemRead) {
  viewing.value = row
  detailVisible.value = true
}

function openEdit(row: SpaceListItemRead) {
  editing.value = row
  editVisible.value = true
}

async function onToggleBan(row: SpaceListItemRead) {
  const isBan = row.status !== 'banned'
  const action = isBan ? '封禁' : '解封'
  try {
    await ElMessageBox.confirm(
      `确认${action}空间「${row.name}」？${isBan ? '封禁后该空间图片不可访问、无法上传' : ''}`,
      `${action}空间`,
      { type: 'warning', confirmButtonText: action, cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    if (isBan) await spaceApi.ban(row.id)
    else await spaceApi.unban(row.id)
    ElMessage.success(`空间已${action}`)
    load()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, `${action}失败`))
  }
}

async function onDelete(row: SpaceListItemRead) {
  try {
    await ElMessageBox.confirm(
      `确认删除空间「${row.name}」？将级联删除该空间下所有图片，此操作不可撤销`,
      '删除空间',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await spaceApi.remove(row.id)
    ElMessage.success('空间已删除')
    load()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '删除失败'))
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-intro"><div class="eyebrow">ADMIN · 空间管理</div><h2 class="page-title">空间管理</h2><p class="page-subtitle">查看空间配额、状态并处理异常空间</p></div>

    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <el-input
          v-model="filters.name"
          placeholder="搜索空间名称"
          clearable
          class="search"
          @keyup.enter="resetAndLoad"
          @clear="resetAndLoad"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <el-input
          v-model="filters.user_id"
          placeholder="所属用户 ID"
          clearable
          class="user-id"
          @keyup.enter="resetAndLoad"
          @clear="resetAndLoad"
        />

        <el-select
          v-model="filters.space_level"
          placeholder="全部级别"
          clearable
          class="level"
          @change="resetAndLoad"
        >
          <el-option
            v-for="o in SPACE_LEVEL_OPTIONS"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
      </div>
    </el-card>

    <el-card class="table-card mobile-table" shadow="never">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="空间名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="所属用户" width="110">
          <template #default="{ row }">#{{ row.user_id }}</template>
        </el-table-column>
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">{{ spaceLevelLabel(row.space_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="容量用量" width="180">
          <template #default="{ row }">
            {{ formatBytes(row.total_size) }} / {{ formatBytes(row.max_size) }}
            <el-tag v-if="row.total_size > row.max_size" size="small" type="danger">超限</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="图片数量" width="120">
          <template #default="{ row }">
            {{ row.total_count }} / {{ row.max_count }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '已封禁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <EmptyValue :value="row.created_at" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link :type="row.status === 'banned' ? 'success' : 'warning'" @click="onToggleBan(row)">
              {{ row.status === 'banned' ? '解封' : '封禁' }}
            </el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="mobile-list">
        <div v-for="row in rows" :key="row.id" class="mobile-card">
          <div class="mobile-body">
            <div class="mobile-title">{{ row.name }} <span class="muted">#{{ row.id }}</span></div>
            <div class="mobile-meta">用户 #{{ row.user_id }} · {{ spaceLevelLabel(row.space_level) }}</div>
            <div class="mobile-meta">{{ formatBytes(row.total_size) }} / {{ formatBytes(row.max_size) }} · {{ row.total_count }}/{{ row.max_count }} 张</div>
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">{{ row.status === 'active' ? '正常' : '已封禁' }}</el-tag>
            <div class="mobile-actions">
              <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button link :type="row.status === 'banned' ? 'success' : 'warning'" size="small" @click="onToggleBan(row)">{{ row.status === 'banned' ? '解封' : '封禁' }}</el-button>
              <el-button link type="danger" size="small" @click="onDelete(row)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

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

    <SpaceDetailDialog v-model="detailVisible" :space="viewing" />
    <SpaceEditDialog v-model="editVisible" :space="editing" @success="load" />
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

.search {
  width: 220px;
}

.user-id {
  width: 140px;
}

.level {
  width: 130px;
}

.table-card {
  border-radius: 10px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
