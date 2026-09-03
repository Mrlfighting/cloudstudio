<script setup lang="ts">
/**
 * 管理员：用户列表管理（分页 + 修改角色）
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userApi } from '@/api/user'
import { getErrorMessage } from '@/api/http'
import type { UserRead, UserRole } from '@/types/user'
import UserAvatar from '@/components/UserAvatar.vue'
import RoleTag from '@/components/RoleTag.vue'
import EmptyValue from '@/components/EmptyValue.vue'

const loading = ref(false)
const rows = ref<UserRead[]>([])
const pagination = reactive({
  page: 1,
  itemsPerPage: 10,
  total: 0,
})

async function load() {
  loading.value = true
  try {
    const res = await userApi.getUsers(pagination.page, pagination.itemsPerPage)
    rows.value = res.data
    pagination.total = res.total_count
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取用户列表失败'))
  } finally {
    loading.value = false
  }
}

function onPageChange() {
  load()
}

function onSizeChange() {
  pagination.page = 1
  load()
}

async function onRoleChange(row: UserRead, newRole: UserRole) {
  const roleLabel = newRole === 'admin' ? '管理员' : '普通用户'
  try {
    await ElMessageBox.confirm(`确认将用户 ${row.username} 的角色改为「${roleLabel}」？`, '修改角色', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消',
    })
  } catch {
    // 取消：重新加载以还原下拉选择
    await load()
    return
  }

  try {
    await userApi.changeRole(row.username, newRole)
    ElMessage.success('用户角色修改成功')
    await load()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '修改角色失败'))
    await load()
  }
}

function oauthLabel(row: UserRead): string {
  if (row.oauth_provider === 'google') return 'Google'
  if (row.oauth_provider === 'github') return 'GitHub'
  return '密码'
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-intro"><div class="eyebrow">ADMIN · 用户管理</div><h2 class="page-title">用户管理</h2><p class="page-subtitle">维护用户状态、角色与会员信息</p></div>

    <el-card class="manage-card">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column label="头像" width="70">
          <template #default="{ row }">
            <UserAvatar :user="row" :size="36" />
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="昵称" min-width="120" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="邮箱" min-width="160">
          <template #default="{ row }">
            <EmptyValue :value="row.email" />
          </template>
        </el-table-column>
        <el-table-column label="角色" width="170">
          <template #default="{ row }">
            <div class="role-cell">
              <RoleTag :role="row.user_role" />
              <el-select
                :model-value="row.user_role"
                size="small"
                style="width: 96px"
                @change="onRoleChange(row, $event as UserRole)"
              >
                <el-option label="用户" value="user" />
                <el-option label="管理员" value="admin" />
              </el-select>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="超管" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" type="danger" size="small">是</el-tag>
            <span v-else>否</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_deleted ? 'danger' : 'success'" size="small" effect="plain">
              {{ row.is_deleted ? '已停用' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册方式" width="100">
          <template #default="{ row }">{{ oauthLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="会员等级" width="100">
          <template #default="{ row }">
            <EmptyValue :value="row.tier_id ? `ID: ${row.tier_id}` : null" />
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
  </div>
</template>

<style scoped>
.manage-card {
  border-radius: 10px;
}

.role-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
