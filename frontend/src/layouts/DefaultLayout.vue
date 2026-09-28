<script setup lang="ts">
/**
 * 默认布局：顶栏（品牌 + 导航 + 用户下拉）+ 主内容区
 */
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAuthGateStore } from '@/stores/authGate'
import UserAvatar from '@/components/UserAvatar.vue'

const router = useRouter()
const auth = useAuthStore()
const authGate = useAuthGateStore()

async function handleLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/pictures')
}

function openAuthentication(mode: 'login' | 'register'): void {
  void authGate.requireAuthentication({
    mode,
    reason: mode === 'login' ? '登录后可使用完整功能' : '注册并登录后可使用完整功能',
  })
}
</script>

<template>
  <el-container class="layout">
    <el-header class="header" height="72px">
      <div class="header-inner">
        <router-link to="/pictures" class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" role="img">
              <path class="brand-cloud" d="M14.7 35.1a6.7 6.7 0 0 1-1.1-13.3 10.6 10.6 0 0 1 20.2 2.6 5.5 5.5 0 0 1-.3 10.9H14.7Z" />
              <path class="brand-spark" d="M35.8 9.6c.5 3 1.9 4.4 4.8 4.9-2.9.5-4.3 1.9-4.8 4.8-.5-2.9-1.9-4.3-4.8-4.8 2.9-.5 4.3-1.9 4.8-4.9Z" />
              <circle class="brand-dot" cx="13" cy="13" r="2.2" />
            </svg>
          </span>
          <span class="brand-copy"><strong>云上工坊</strong><small>CLOUD ATELIER</small></span>
        </router-link>

        <!-- router 属性：让 el-menu-item 的 index 作为路由路径，点击自动导航 -->
        <el-menu mode="horizontal" router :default-active="$route.path" :ellipsis="false" class="nav">
          <el-menu-item index="/pictures"><el-icon><Compass /></el-icon>探索</el-menu-item>
          <el-menu-item index="/pixel-beads"><el-icon><Grid /></el-icon>拼豆工坊</el-menu-item>
          <el-menu-item index="/spaces/color-search"><el-icon><Brush /></el-icon>颜色搜图</el-menu-item>
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
        <div v-else class="guest-actions">
          <el-button text @click="openAuthentication('login')">登录</el-button>
          <el-button type="primary" @click="openAuthentication('register')">注册</el-button>
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
  position: relative;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.88);
  border-radius: 13px;
  background:
    radial-gradient(circle at 25% 20%, rgba(255,255,255,.72), transparent 28%),
    linear-gradient(145deg, #82d3ef 3%, #aaa9ed 50%, #f58daf 100%);
  box-shadow: 0 8px 18px rgba(102,151,207,.24), inset 0 1px 0 rgba(255,255,255,.72);
  transform: rotate(-2deg);
  transition: transform .25s ease, box-shadow .25s ease;
}
.brand:hover .brand-mark {
  transform: rotate(2deg) translateY(-1px);
  box-shadow: 0 11px 22px rgba(216,111,154,.28), inset 0 1px 0 rgba(255,255,255,.8);
}
.brand-mark::after {
  position: absolute;
  inset: 3px;
  content: '';
  pointer-events: none;
  border: 1px solid rgba(255,255,255,.24);
  border-radius: 10px;
}
.brand-mark svg { width: 32px; height: 32px; overflow: visible; }
.brand-cloud { fill: rgba(255,255,255,.97); filter: drop-shadow(0 2px 2px rgba(76,99,150,.16)); }
.brand-spark { fill: #fff1a8; }
.brand-dot { fill: rgba(255,255,255,.78); }
.brand-copy { display: flex; flex-direction: column; line-height: 1; letter-spacing: 1px; }
.brand-copy strong { font-size: 16px; font-weight: 900; }
.brand-copy small { margin-top: 5px; color: var(--app-muted); font-size: 7px; letter-spacing: 1.35px; }
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

.guest-actions { display: flex; align-items: center; gap: 4px; white-space: nowrap; }

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
  .header {
    height: auto !important;
    padding: 0 max(12px, env(safe-area-inset-left)) 0 max(12px, env(safe-area-inset-right));
  }
  .header-inner {
    height: auto;
    min-height: 108px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: 58px 50px;
    gap: 0 12px;
  }
  .brand { grid-column: 1; grid-row: 1; width: max-content; }
  .brand-copy { display: flex; }
  .brand-copy small { display: none; }
  .nav {
    grid-column: 1 / -1;
    grid-row: 2;
    width: calc(100vw - max(12px, env(safe-area-inset-left)) - max(12px, env(safe-area-inset-right)));
    margin: 0;
    mask-image: linear-gradient(90deg, transparent, #000 12px, #000 calc(100% - 18px), transparent);
    -webkit-mask-image: linear-gradient(90deg, transparent, #000 12px, #000 calc(100% - 18px), transparent);
    scroll-snap-type: x proximity;
    overscroll-behavior-inline: contain;
  }
  .nav :deep(.el-menu-item) {
    height: 50px;
    min-height: 44px;
    padding: 0 12px;
    font-size: 12px;
    scroll-snap-align: start;
  }
  .nav :deep(.el-menu-item:first-child) { margin-left: 4px; }
  .user-area, .guest-actions { grid-column: 2; grid-row: 1; justify-self: end; }
  .user-trigger { min-width: 44px; min-height: 44px; justify-content: flex-end; }
  .guest-actions .el-button:first-child { display: inline-flex; }
  .guest-actions .el-button { min-width: 0; min-height: 40px; padding: 8px 10px; }
}
</style>
