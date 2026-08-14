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
    <el-header class="header">
      <div class="header-inner">
        <router-link to="/profile" class="brand">
          <el-icon :size="22"><UserFilled /></el-icon>
          <span>用户中心</span>
        </router-link>

        <!-- router 属性：让 el-menu-item 的 index 作为路由路径，点击自动导航 -->
        <el-menu mode="horizontal" router :default-active="$route.path" :ellipsis="false" class="nav">
          <el-menu-item index="/profile">个人中心</el-menu-item>
          <el-menu-item index="/profile/edit">编辑资料</el-menu-item>
          <el-menu-item index="/pictures">图片库</el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/pictures/manage">图片管理</el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/admin/users">用户管理</el-menu-item>
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
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
}

.header-inner {
  max-width: 1080px;
  margin: 0 auto;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  text-decoration: none;
  white-space: nowrap;
}

.nav {
  flex: 1;
  border-bottom: none;
}

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
  color: #303133;
}

.main {
  padding: 0;
}
</style>
