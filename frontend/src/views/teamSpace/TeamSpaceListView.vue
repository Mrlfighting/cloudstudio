<script setup lang="ts">
/**
 * 团队空间列表：我创建 + 我加入的团队
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { formatBytes } from '@/types/space'
import { spaceRoleLabel, type TeamSpaceListItemRead } from '@/types/teamSpace'

const router = useRouter()
const loading = ref(false)
const teams = ref<TeamSpaceListItemRead[]>([])

function roleTagType(role: string): 'warning' | 'success' | 'info' {
  if (role === 'admin') return 'warning'
  if (role === 'editor') return 'success'
  return 'info'
}

async function load() {
  loading.value = true
  try {
    teams.value = await teamSpaceApi.listMyTeams()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取团队列表失败'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="header">
      <h2 class="page-title">团队空间</h2>
      <el-button type="primary" :icon="'Plus'" @click="router.push('/spaces/team/create')">
        创建团队空间
      </el-button>
    </div>

    <div v-loading="loading" class="grid">
      <el-card
        v-for="t in teams"
        :key="t.id"
        class="team-card"
        shadow="hover"
        @click="router.push(`/spaces/team/${t.id}`)"
      >
        <div class="team-name">{{ t.name }}</div>
        <div class="team-meta">
          <el-tag size="small" :type="roleTagType(t.space_role)">{{ spaceRoleLabel(t.space_role) }}</el-tag>
          <span class="muted">{{ t.total_count }} 张 · {{ formatBytes(t.total_size) }}</span>
        </div>
      </el-card>
    </div>

    <el-empty v-if="!loading && teams.length === 0" description="暂无团队空间，点击右上角创建" />
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.team-card {
  border-radius: 10px;
  cursor: pointer;
}

.team-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.team-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.muted {
  color: #909399;
  font-size: 13px;
}
</style>
