<script setup lang="ts">
/**
 * 团队空间列表：我创建 + 我加入的团队
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import PageIntro from '@/components/PageIntro.vue'
import StatCard from '@/components/StatCard.vue'
import { formatBytes } from '@/types/space'
import { spaceRoleLabel, type TeamSpaceListItemRead } from '@/types/teamSpace'

const router = useRouter()
const loading = ref(false)
const teams = ref<TeamSpaceListItemRead[]>([])

const teamCount = computed(() => teams.value.length)
const adminCount = computed(() => teams.value.filter((team) => team.space_role === 'admin').length)
const editorCount = computed(() => teams.value.filter((team) => team.space_role === 'editor').length)
const totalImages = computed(() => teams.value.reduce((sum, team) => sum + (team.total_count ?? 0), 0))

const recentTeams = computed(() => teams.value.slice(0, 3))

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
  <div class="team-page page-container">
    <PageIntro eyebrow="COLLABORATION · 协作空间" title="团队空间" subtitle="与团队一起整理素材、共创灵感" />

    <section class="team-layout">
      <aside class="team-sidebar">
        <el-card class="side-card" shadow="never">
          <div class="team-head">
            <div>
              <div class="team-name">团队工作台</div>
              <div class="small-muted">统一查看协作空间、角色和容量</div>
            </div>
          </div>

          <div class="side-kpis">
            <div class="side-kpi">
              <span>团队总数</span>
              <strong>{{ teamCount }}</strong>
            </div>
            <div class="side-kpi">
              <span>管理权限</span>
              <strong>{{ adminCount }}</strong>
            </div>
            <div class="side-kpi">
              <span>编辑权限</span>
              <strong>{{ editorCount }}</strong>
            </div>
            <div class="side-kpi">
              <span>图片总量</span>
              <strong>{{ totalImages }}</strong>
            </div>
          </div>
        </el-card>

        <el-card class="side-card" shadow="never">
          <div class="side-head">
            <h3>最近进入</h3>
            <span class="small-muted">按最近打开排序</span>
          </div>
          <div class="side-list">
            <button
              v-for="team in recentTeams"
              :key="team.id"
              class="side-list-item"
              @click="router.push(`/spaces/team/${team.id}`)"
            >
              <div class="side-list-copy">
                <strong>{{ team.name }}</strong>
                <span>{{ team.total_count }} 张 · {{ formatBytes(team.total_size) }}</span>
              </div>
              <el-tag size="small" :type="roleTagType(team.space_role)" effect="plain">
                {{ spaceRoleLabel(team.space_role) }}
              </el-tag>
            </button>
          </div>
        </el-card>

        <el-card class="side-card" shadow="never">
          <div class="side-head">
            <h3>协作提示</h3>
          </div>
          <div class="tips-list">
            <div>• 进入团队后可继续上传、审核和分工。</div>
            <div>• 管理员可邀请成员并调整权限。</div>
            <div>• 右上角可快速创建新的协作空间。</div>
          </div>
        </el-card>
      </aside>

      <main class="team-main">
        <div class="stat-grid">
          <StatCard label="团队总数" :value="teamCount" />
          <StatCard label="管理角色" :value="adminCount" />
          <StatCard label="编辑角色" :value="editorCount" />
          <StatCard label="总图片数" :value="totalImages" />
        </div>

        <el-card class="team-card-panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <div>
                <div class="panel-title">我的团队</div>
                <div class="small-muted">点击进入团队工作台继续协作</div>
              </div>
              <el-button type="primary" :icon="'Plus'" @click="router.push('/spaces/team/create')">
                创建团队空间
              </el-button>
            </div>
          </template>

          <div v-loading="loading" class="team-grid">
            <el-card
              v-for="team in teams"
              :key="team.id"
              class="team-card"
              shadow="never"
              @click="router.push(`/spaces/team/${team.id}`)"
            >
              <div class="team-card-top">
                <div class="team-card-icon">{{ team.name.slice(0, 1).toUpperCase() }}</div>
                <el-tag size="small" :type="roleTagType(team.space_role)" effect="plain">
                  {{ spaceRoleLabel(team.space_role) }}
                </el-tag>
              </div>
              <div class="team-card-name">{{ team.name }}</div>
              <div class="team-card-desc">协作空间 · 继续整理素材、审核内容与同步进度</div>
              <div class="team-card-meta">
                <span>{{ team.total_count }} 张</span>
                <span>{{ formatBytes(team.total_size) }}</span>
              </div>
            </el-card>
          </div>

          <el-empty v-if="!loading && teams.length === 0" description="暂无团队空间，点击右上角创建" />
        </el-card>

        <el-card class="team-card-panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <div>
                <div class="panel-title">协作建议</div>
                <div class="small-muted">参考原型里的工作台信息密度</div>
              </div>
            </div>
          </template>

          <div class="suggest-grid">
            <div class="suggest-card">
              <strong>统一上传入口</strong>
              <span>团队空间内的素材上传、筛选与整理保持同一套入口。</span>
            </div>
            <div class="suggest-card">
              <strong>角色驱动操作</strong>
              <span>管理员、编辑者和查看者的权限状态清晰可见。</span>
            </div>
            <div class="suggest-card">
              <strong>信息密度更高</strong>
              <span>采用更接近花瓣的卡片、留白和层次感。</span>
            </div>
          </div>
        </el-card>
      </main>
    </section>
  </div>
</template>

<style scoped>
.team-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.team-sidebar {
  display: grid;
  gap: 16px;
}

.side-card,
.team-card-panel {
  border-radius: var(--app-radius-lg) !important;
}

.team-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.team-name {
  font-size: 20px;
  font-weight: 800;
  color: var(--app-ink);
}

.small-muted {
  color: #8d96a2;
  font-size: 12px;
}

.side-kpis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
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

.side-list {
  display: grid;
  gap: 10px;
}

.side-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fbfcfe;
  border: 1px solid var(--app-line-soft);
  cursor: pointer;
  text-align: left;
}

.side-list-item:hover {
  background: #f6f7fb;
}

.side-list-copy {
  min-width: 0;
}

.side-list-copy strong {
  display: block;
  color: var(--app-ink);
  font-size: 14px;
}

.side-list-copy span {
  display: block;
  margin-top: 4px;
  color: #8d96a2;
  font-size: 12px;
}

.tips-list {
  display: grid;
  gap: 10px;
  color: #6f7782;
  font-size: 13px;
  line-height: 1.7;
}

.team-main {
  min-width: 0;
  display: grid;
  gap: 16px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.team-card-panel {
  padding: 4px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--app-ink);
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.team-card {
  border-radius: 18px !important;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  border: 1px solid var(--app-line-soft) !important;
  background:
    linear-gradient(145deg, rgba(255,255,255,.96), rgba(250,252,255,.96));
}

.team-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 30px rgba(38,42,52,.11) !important;
}

.team-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.team-card-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  color: #fff;
  font-weight: 800;
  background: linear-gradient(135deg, var(--app-blue), var(--app-primary));
  box-shadow: 8px 8px 0 rgba(236,114,150,.12);
}

.team-card-name {
  font-size: 18px;
  font-weight: 800;
  color: var(--app-ink);
  margin-bottom: 8px;
}

.team-card-desc {
  color: #8d96a2;
  font-size: 13px;
  line-height: 1.7;
  min-height: 48px;
}

.team-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  color: #7b8490;
  font-size: 12px;
}

.suggest-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.suggest-card {
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--app-line-soft);
}

.suggest-card strong {
  display: block;
  font-size: 14px;
  color: var(--app-ink);
}

.suggest-card span {
  display: block;
  margin-top: 8px;
  color: #8d96a2;
  font-size: 12px;
  line-height: 1.7;
}

@media (max-width: 1080px) {
  .team-layout {
    grid-template-columns: 1fr;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .suggest-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .side-kpis {
    grid-template-columns: 1fr;
  }

  .team-grid {
    grid-template-columns: 1fr;
  }
}
</style>
