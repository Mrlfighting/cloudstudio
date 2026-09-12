<script setup lang="ts">
/**
 * 默认布局：顶栏（品牌 + 导航 + 用户下拉）+ 主内容区
 */
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/UserAvatar.vue'

const router = useRouter()
const auth = useAuthStore()

async function handleLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-header class="header" height="72px">
      <div class="header-inner">
        <router-link to="/pictures" class="brand">
          <span class="brand-mark"><el-icon :size="18"><Picture /></el-icon></span>
          <span class="brand-copy"><strong>云上工坊</strong><small>WORKSHOP</small></span>
        </router-link>

        <!-- router 属性：让 el-menu-item 的 index 作为路由路径，点击自动导航 -->
        <el-menu mode="horizontal" router :default-active="$route.path" :ellipsis="false" class="nav">
          <el-menu-item index="/pictures"><el-icon><Compass /></el-icon>探索</el-menu-item>
          <el-menu-item index="/profile"><el-icon><User /></el-icon>个人中心</el-menu-item>
          <el-menu-item index="/spaces"><el-icon><FolderOpened /></el-icon>我的空间</el-menu-item>
          <el-menu-item index="/spaces/team"><el-icon><UserFilled /></el-icon>团队空间</el-menu-item>
          <el-menu-item index="/analytics/my-space"><el-icon><DataAnalysis /></el-icon>数据分析</el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/admin/analytics"><el-icon><Monitor /></el-icon>管理后台</el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/pictures/manage"><el-icon><Picture /></el-icon>图片审核</el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/admin/users"><el-icon><UserFilled /></el-icon>成员管理</el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/spaces/manage"><el-icon><FolderOpened /></el-icon>空间管理</el-menu-item>
        </el-menu>

        <div v-if="auth.user" class="user-area">
          <el-dropdown trigger="click">
            <span class="user-trigger">
              <UserAvatar :user="auth.user" :size="30" />
              <span class="user-name">{{ auth.user.name }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/profile')">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item @click="router.push('/profile/edit')">
                  <el-icon><Edit /></el-icon>编辑资料
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-header>

    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100%;
}

.header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(255,255,255,.86);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(231,233,239,.8);
  padding: 0 var(--app-page-x);
}

.header-inner {
  max-width: var(--app-width);
  margin: 0 auto;
  height: 72px;
  display: flex;
  align-items: center;
  gap: 34px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--app-ink);
  text-decoration: none;
  white-space: nowrap;
}

.brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  color: #fff;
  border-radius: 13px 5px 13px 5px;
  background: linear-gradient(145deg, var(--app-blue), var(--app-primary));
  box-shadow: 7px 7px 0 rgba(236,114,150,.13);
}
.brand-copy { display: flex; flex-direction: column; line-height: 1; letter-spacing: 1px; }
.brand-copy strong { font-size: 16px; font-weight: 900; }
.brand-copy small { margin-top: 4px; color: var(--app-muted); font-size: 8px; letter-spacing: 2px; }
.nav {
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
  border-bottom: none;
  background: transparent;
}
.nav::-webkit-scrollbar { display: none; }
.nav :deep(.el-menu-item) { flex-shrink: 0; white-space: nowrap; height: 72px; border-bottom: 2px solid transparent; color: var(--app-text); font-weight: 600; gap: 5px; }
.nav :deep(.el-menu-item:hover) { color: var(--app-primary-dark); background: transparent; }
.nav :deep(.el-menu-item.is-active) { color: var(--app-primary-dark); border-bottom-color: var(--app-primary); }

.user-area {
  display: flex;
  align-items: center;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.user-name {
  font-size: 14px;
  color: var(--app-ink);
  font-weight: 600;
}

.main {
  padding: 0;
}
@media (max-width: 1280px) {
  .header-inner { gap: 16px; }
  .nav :deep(.el-menu-item) { padding: 0 12px; font-size: 13px; }
  .user-name { display: none; }
}
@media (max-width: 900px) {
  .nav :deep(.el-menu-item) { padding: 0 10px; }
}
@media (max-width: 560px) {
  .header { padding: 0 14px; }
  .header-inner { height: 62px; }
  .brand-copy { display: none; }
  .nav :deep(.el-menu-item) { height: 62px; }
}
</style>
