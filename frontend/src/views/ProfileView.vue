<script setup lang="ts">
/**
 * 个人中心：展示当前用户信息
 */
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import PageIntro from '@/components/PageIntro.vue'
import RoleTag from '@/components/RoleTag.vue'
import StatCard from '@/components/StatCard.vue'
import UserAvatar from '@/components/UserAvatar.vue'
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
  if (!auth.user) {
    try {
      const me = await userApi.getMe()
      auth.setUser(me)
    } catch {
      ElMessage.error('获取用户信息失败')
    }
  }
})
</script>

<template>
  <div class="profile-page page-container">
    <PageIntro eyebrow="PROFILE · 个人资料" title="个人中心" subtitle="管理你的账号信息与创作身份" />

    <section v-if="user" class="profile-layout">
      <aside class="profile-sidebar">
        <el-card class="side-card" shadow="never">
          <div class="side-profile">
            <UserAvatar :user="user" :size="68" />
            <div class="side-profile-copy">
              <div class="side-profile-name">
                {{ user.name }}
                <RoleTag :role="user.user_role" />
              </div>
              <div class="side-profile-account">@{{ user.username }}</div>
            </div>
          </div>

          <div class="side-kpis">
            <div class="side-kpi">
              <span>账号 ID</span>
              <strong>{{ user.id }}</strong>
            </div>
            <div class="side-kpi">
              <span>注册方式</span>
              <strong>{{ loginMethod }}</strong>
            </div>
          </div>
        </el-card>

        <el-card class="side-card" shadow="never">
          <div class="side-head">
            <h3>身份概览</h3>
            <span class="small-muted">当前账号状态</span>
          </div>
          <div class="side-list">
            <div class="side-row">
              <span>邮箱</span>
              <strong><EmptyValue :value="user.email" /></strong>
            </div>
            <div class="side-row">
              <span>邮箱认证</span>
              <el-tag :type="user.email_verified ? 'success' : 'info'" size="small" effect="plain">
                {{ user.email_verified ? '已认证' : '未认证' }}
              </el-tag>
            </div>
            <div class="side-row">
              <span>会员等级</span>
              <strong>{{ tierLabel }}</strong>
            </div>
            <div class="side-row">
              <span>简介</span>
              <strong><EmptyValue :value="user.user_profile" /></strong>
            </div>
          </div>
        </el-card>
      </aside>

      <main class="profile-main">
        <el-card class="profile-card" shadow="never">
          <div class="profile-card-head">
            <div class="profile-header">
              <UserAvatar :user="user" :size="72" />
              <div class="profile-summary">
                <div class="summary-name">
                  {{ user.name }}
                  <RoleTag :role="user.user_role" />
                </div>
                <div class="summary-account">@{{ user.username }}</div>
              </div>
            </div>

            <el-button type="primary" @click="router.push('/profile/edit')">
              <el-icon style="margin-right: 4px"><Edit /></el-icon>编辑资料
            </el-button>
          </div>

          <div class="profile-metrics">
            <StatCard label="账号 ID" :value="user.id" />
            <StatCard label="注册方式" :value="loginMethod" />
            <StatCard label="邮箱状态" :value="user.email_verified ? '已认证' : '未认证'" />
            <StatCard label="会员等级" :value="tierLabel" />
          </div>

          <el-descriptions :column="1" border class="profile-desc">
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
          </el-descriptions>
        </el-card>
      </main>
    </section>
  </div>
</template>

<style scoped>
.profile-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.profile-sidebar {
  display: grid;
  gap: 16px;
}

.side-card,
.profile-card {
  border-radius: var(--app-radius-lg) !important;
}

.side-card {
  overflow: hidden;
}

.side-profile {
  display: flex;
  align-items: center;
  gap: 14px;
}

.side-profile-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 800;
  color: var(--app-ink);
}

.side-profile-account {
  margin-top: 4px;
  color: #909399;
}

.side-kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 18px;
}

.side-kpi {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--app-line-soft);
}

.side-kpi span {
  display: block;
  color: var(--app-muted);
  font-size: 12px;
}

.side-kpi strong {
  display: block;
  margin-top: 8px;
  color: var(--app-ink);
  font-size: 15px;
  font-weight: 800;
}

.side-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}

.side-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--app-ink);
}

.small-muted {
  color: #8d96a2;
  font-size: 12px;
}

.side-list {
  display: grid;
  gap: 10px;
}

.side-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fbfcfe;
  border: 1px solid var(--app-line-soft);
}

.side-row span {
  color: var(--app-muted);
  font-size: 12px;
}

.side-row strong {
  font-size: 13px;
  color: var(--app-ink);
}

.profile-main {
  min-width: 0;
}

.profile-card {
  padding: 4px;
}

.profile-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 8px 18px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.profile-summary {
  flex: 1;
}

.summary-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 24px;
  font-weight: 800;
  color: var(--app-ink);
}

.summary-account {
  margin-top: 4px;
  font-size: 14px;
  color: #909399;
}

.profile-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  padding: 0 8px 14px;
}

.profile-desc {
  margin: 8px 8px 8px;
}

@media (max-width: 1080px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }

  .profile-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .profile-metrics {
    grid-template-columns: 1fr;
  }

  .profile-card-head {
    flex-direction: column;
  }

  .profile-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .profile-sidebar {
    gap: 12px;
  }

  .side-kpis {
    grid-template-columns: 1fr;
  }
}
</style>
