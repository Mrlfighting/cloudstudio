<script setup lang="ts">
/**
 * 个人中心：展示当前用户信息
 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/UserAvatar.vue'
import RoleTag from '@/components/RoleTag.vue'
import EmptyValue from '@/components/EmptyValue.vue'

const router = useRouter()
const auth = useAuthStore()

const user = computed(() => auth.user)

const loginMethod = computed(() => {
  const p = user.value?.oauth_provider
  if (p === 'google') return 'Google'
  if (p === 'github') return 'GitHub'
  return '密码'
})

const tierLabel = computed(() => (user.value?.tier_id ? `ID: ${user.value.tier_id}` : '未开通'))

onMounted(async () => {
  // 硬刷新后 store 无用户时重新拉取
  if (!auth.user) {
    try {
      const me = await userApi.getMe()
      auth.setUser(me)
    } catch (err) {
      ElMessage.error('获取用户信息失败')
    }
  }
})
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">个人中心</h2>

    <el-card v-if="user" class="profile-card">
      <div class="profile-header">
        <UserAvatar :user="user" :size="72" />
        <div class="profile-summary">
          <div class="summary-name">
            {{ user.name }}
            <RoleTag :role="user.user_role" />
          </div>
          <div class="summary-account">@{{ user.username }}</div>
        </div>
        <div class="profile-actions">
          <el-button type="primary" @click="router.push('/profile/edit')">
            <el-icon style="margin-right: 4px"><Edit /></el-icon>编辑资料
          </el-button>
        </div>
      </div>

      <el-descriptions :column="1" border class="profile-desc">
        <el-descriptions-item label="账号 ID">{{ user.id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">
          <EmptyValue :value="user.email" />
        </el-descriptions-item>
        <el-descriptions-item label="简介">
          <EmptyValue :value="user.user_profile" />
        </el-descriptions-item>
        <el-descriptions-item label="角色">
          <RoleTag :role="user.user_role" />
        </el-descriptions-item>
        <el-descriptions-item label="邮箱认证">
          <el-tag :type="user.email_verified ? 'success' : 'info'" size="small" effect="plain">
            {{ user.email_verified ? '已认证' : '未认证' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册方式">{{ loginMethod }}</el-descriptions-item>
        <el-descriptions-item label="会员等级">{{ tierLabel }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.profile-card {
  border-radius: 10px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 8px 8px 24px;
}

.profile-summary {
  flex: 1;
}

.summary-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.summary-account {
  margin-top: 4px;
  font-size: 14px;
  color: #909399;
}

.profile-desc {
  margin-top: 8px;
}
</style>
