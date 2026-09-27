<script setup lang="ts">
/** 团队空间列表：只调整视觉层级，接口、权限与路由行为保持不变。 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { EditPen, Key, PictureFilled, Plus, Refresh, UserFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import StatCard from '@/components/StatCard.vue'
import { formatBytes, type SpaceInfoRead } from '@/types/space'
import { spaceRoleLabel, type TeamSpaceListItemRead } from '@/types/teamSpace'

const router = useRouter()
const loading = ref(false)
const teams = ref<TeamSpaceListItemRead[]>([])
const ownedTeam = ref<SpaceInfoRead | null>(null)
const ownedTeamState = ref<'loading' | 'exists' | 'missing' | 'error'>('loading')

const teamCount = computed(() => teams.value.length)
const adminCount = computed(() => teams.value.filter((team) => team.space_role === 'admin').length)
const editorCount = computed(() => teams.value.filter((team) => team.space_role === 'editor').length)
const viewerCount = computed(() => teams.value.filter((team) => team.space_role === 'viewer').length)
const totalImages = computed(() => teams.value.reduce((sum, team) => sum + (team.total_count ?? 0), 0))
const totalSize = computed(() => teams.value.reduce((sum, team) => sum + (team.total_size ?? 0), 0))
const recentTeams = computed(() => teams.value.slice(0, 3))

function roleTagType(role: string): 'warning' | 'success' | 'info' {
  if (role === 'admin') return 'warning'
  if (role === 'editor') return 'success'
  return 'info'
}

function roleClass(role: string): string {
  if (role === 'admin') return 'is-admin'
  if (role === 'editor') return 'is-editor'
  return 'is-viewer'
}

function teamUsage(team: TeamSpaceListItemRead): number {
  const countRate = team.max_count > 0 ? team.total_count / team.max_count : 0
  const sizeRate = team.max_size > 0 ? team.total_size / team.max_size : 0
  return Math.min(100, Math.round(Math.max(countRate, sizeRate) * 100))
}

function usageColor(percentage: number): string {
  if (percentage >= 90) return '#ef6f78'
  if (percentage >= 70) return '#ec9a72'
  return '#68cdb5'
}

function formatTeamDate(value: string | null): string {
  if (!value) return '创建时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '创建时间未知'
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')} 创建`
}

function openPrimaryTeamAction(): void {
  if (ownedTeamState.value === 'exists' && ownedTeam.value) {
    router.push(`/spaces/team/${ownedTeam.value.id}`)
    return
  }
  if (ownedTeamState.value === 'missing') router.push('/spaces/team/create')
}

async function load() {
  loading.value = true
  ownedTeam.value = null
  ownedTeamState.value = 'loading'

  const [teamsResult, ownedTeamResult] = await Promise.allSettled([
    teamSpaceApi.listMyTeams(),
    teamSpaceApi.getMyTeam(),
  ])

  if (teamsResult.status === 'fulfilled') {
    teams.value = teamsResult.value
  } else {
    teams.value = []
    ElMessage.error(getErrorMessage(teamsResult.reason, '获取团队列表失败'))
  }

  if (ownedTeamResult.status === 'fulfilled') {
    ownedTeam.value = ownedTeamResult.value
    ownedTeamState.value = 'exists'
  } else {
    const status = (ownedTeamResult.reason as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      ownedTeamState.value = 'missing'
    } else {
      ownedTeamState.value = 'error'
      ElMessage.warning(getErrorMessage(ownedTeamResult.reason, '无法确认已创建的团队空间'))
    }
  }

  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="team-page page-container">
    <section class="team-hero analytics-reveal">
      <span class="hero-orb hero-orb--sky" aria-hidden="true"></span>
      <span class="hero-orb hero-orb--rose" aria-hidden="true"></span>
      <div class="hero-pixels" aria-hidden="true"><i v-for="index in 8" :key="index"></i></div>

      <div class="team-hero__content">
        <div class="eyebrow">COLLABORATION · 团队协作</div>
        <h1>让灵感在团队里<br /><span>持续生长</span></h1>
        <p>在同一个空间整理素材、共享进度，让每位成员都清楚下一步要做什么。</p>
        <div class="hero-actions">
          <el-button
            type="primary"
            size="large"
            :loading="ownedTeamState === 'loading'"
            :disabled="ownedTeamState === 'error'"
            @click="openPrimaryTeamAction"
          >
            {{ ownedTeamState === 'exists' ? '进入我创建的团队' : '创建团队空间' }}
            <el-icon class="button-arrow"><ArrowRight /></el-icon>
          </el-button>
          <el-button size="large" :icon="Refresh" :loading="loading" @click="load">刷新数据</el-button>
        </div>
      </div>

      <div class="team-hero__visual" aria-hidden="true">
        <div class="member-stack">
          <span class="member-avatar member-avatar--rose">创</span>
          <span class="member-avatar member-avatar--sky">编</span>
          <span class="member-avatar member-avatar--mint">阅</span>
          <span class="member-avatar member-avatar--more">+{{ teamCount }}</span>
        </div>
        <div class="visual-card">
          <div class="visual-card__top"><span>协作概览</span><i></i></div>
          <strong>{{ totalImages }}</strong>
          <small>张素材正在团队空间中流转</small>
          <div class="visual-wave"><i></i><i></i><i></i><i></i><i></i><i></i></div>
        </div>
      </div>
    </section>

    <el-alert
      v-if="ownedTeamState === 'error'"
      class="owner-alert analytics-reveal"
      type="warning"
      title="暂时无法确认你是否已创建团队空间，请刷新后重试"
      show-icon
      :closable="false"
    />

    <section class="stat-grid">
      <StatCard label="参与团队" :value="teamCount" description="当前加入的全部协作空间" :icon="UserFilled" accent="rose" :delay="60" />
      <StatCard label="管理角色" :value="adminCount" description="可管理成员与空间配置" :icon="Key" accent="lavender" :delay="120" />
      <StatCard label="编辑角色" :value="editorCount" description="可整理与更新团队素材" :icon="EditPen" accent="mint" :delay="180" />
      <StatCard label="团队素材" :value="totalImages" hint="张" :description="`共占用 ${formatBytes(totalSize)}`" :icon="PictureFilled" accent="sky" :delay="240" />
    </section>

    <section class="team-workspace">
      <main class="team-panel analytics-reveal" style="--reveal-delay: 280ms">
        <div class="panel-header">
          <div>
            <div class="panel-kicker">MY WORKSPACES</div>
            <h2>我的团队</h2>
            <p>选择一个空间，继续整理素材和推进协作。</p>
          </div>
          <div class="role-summary" aria-label="团队角色统计">
            <span><i class="is-admin"></i>管理 {{ adminCount }}</span>
            <span><i class="is-editor"></i>编辑 {{ editorCount }}</span>
            <span><i class="is-viewer"></i>查看 {{ viewerCount }}</span>
          </div>
        </div>

        <div v-loading="loading" class="team-grid">
          <button
            v-for="(team, index) in teams"
            :key="team.id"
            class="team-card"
            :class="roleClass(team.space_role)"
            :style="{ '--card-delay': `${index * 70}ms` }"
            @click="router.push(`/spaces/team/${team.id}`)"
          >
            <span class="team-card__glow" aria-hidden="true"></span>
            <div class="team-card__top">
              <div class="team-card__identity">
                <span class="team-card__avatar">{{ team.name.slice(0, 1).toUpperCase() }}</span>
                <span><strong>{{ team.name }}</strong><small>{{ formatTeamDate(team.created_at) }}</small></span>
              </div>
              <el-tag size="small" :type="roleTagType(team.space_role)" effect="light">{{ spaceRoleLabel(team.space_role) }}</el-tag>
            </div>

            <div class="team-card__metrics">
              <span><small>素材数量</small><strong>{{ team.total_count }} <em>张</em></strong></span>
              <span><small>占用空间</small><strong>{{ formatBytes(team.total_size) }}</strong></span>
            </div>
            <div class="team-card__quota">
              <div><span>综合用量</span><strong>{{ teamUsage(team) }}%</strong></div>
              <el-progress :percentage="teamUsage(team)" :stroke-width="7" :show-text="false" :color="usageColor(teamUsage(team))" />
            </div>
            <div class="team-card__footer">
              <span>{{ team.total_count }} / {{ team.max_count }} 张</span>
              <span>进入工作台 <el-icon><ArrowRight /></el-icon></span>
            </div>
          </button>
        </div>

        <div v-if="!loading && teams.length === 0" class="empty-team">
          <div class="empty-team__pixels" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
          <h3>还没有加入团队空间</h3>
          <p>创建一个属于你的团队，把素材和灵感集中起来。</p>
          <el-button v-if="ownedTeamState === 'missing'" type="primary" @click="router.push('/spaces/team/create')">创建第一个团队</el-button>
        </div>
      </main>

      <aside class="team-side">
        <section class="side-panel owner-panel analytics-reveal" style="--reveal-delay: 340ms">
          <div class="side-panel__heading">
            <span class="side-icon"><el-icon><OfficeBuilding /></el-icon></span>
            <div><small>OWNER SPACE</small><h3>我创建的团队</h3></div>
          </div>
          <template v-if="ownedTeamState === 'exists' && ownedTeam">
            <div class="owned-team-name">{{ ownedTeam.name }}</div>
            <p>{{ ownedTeam.total_count }} 张素材 · 已用 {{ formatBytes(ownedTeam.total_size) }}</p>
            <el-button type="primary" plain @click="router.push(`/spaces/team/${ownedTeam.id}`)">打开团队</el-button>
          </template>
          <template v-else-if="ownedTeamState === 'missing'">
            <p>你还可以创建一个自己的团队空间，邀请成员共同维护素材。</p>
            <el-button type="primary" plain :icon="Plus" @click="router.push('/spaces/team/create')">立即创建</el-button>
          </template>
          <template v-else><el-skeleton :rows="2" animated /></template>
        </section>

        <section class="side-panel analytics-reveal" style="--reveal-delay: 400ms">
          <div class="side-panel__heading compact">
            <span class="side-icon side-icon--sky"><el-icon><Clock /></el-icon></span>
            <div><small>QUICK ACCESS</small><h3>快速进入</h3></div>
          </div>
          <div v-if="recentTeams.length" class="recent-list">
            <button v-for="team in recentTeams" :key="team.id" @click="router.push(`/spaces/team/${team.id}`)">
              <span class="recent-avatar">{{ team.name.slice(0, 1).toUpperCase() }}</span>
              <span><strong>{{ team.name }}</strong><small>{{ team.total_count }} 张 · {{ formatBytes(team.total_size) }}</small></span>
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
          <p v-else class="side-empty">加入团队后，最近使用的空间会显示在这里。</p>
        </section>

        <section class="side-panel guide-panel analytics-reveal" style="--reveal-delay: 460ms">
          <div class="guide-badge">协作小贴士</div>
          <h3>让团队空间更清晰</h3>
          <ul>
            <li><span>01</span>按项目或内容主题整理素材</li>
            <li><span>02</span>根据职责分配成员权限</li>
            <li><span>03</span>定期检查空间用量与素材</li>
          </ul>
        </section>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.team-page { position: relative; }
.team-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1.16fr) minmax(320px, .84fr); min-height: 330px; margin-bottom: 22px; padding: clamp(30px, 5vw, 58px); overflow: hidden; border: 1px solid rgba(255,255,255,.88); border-radius: 30px; background: linear-gradient(122deg, rgba(232,248,253,.96) 0%, rgba(255,247,250,.97) 54%, rgba(242,237,255,.94) 100%); box-shadow: 0 24px 70px rgba(69, 74, 94, .1); }
.team-hero::after { content: ''; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(105deg, rgba(255,255,255,.34), transparent 38%, rgba(255,255,255,.36)); }
.team-hero__content { position: relative; z-index: 3; align-self: center; }
.team-hero h1 { margin: 0; color: #171b22; font-size: clamp(36px, 4.1vw, 60px); line-height: 1.08; letter-spacing: -2.4px; font-weight: 900; }
.team-hero h1 span { color: transparent; background: linear-gradient(90deg, #cf6787, #788ddc); background-clip: text; -webkit-background-clip: text; }
.team-hero p { max-width: 600px; margin: 20px 0 0; color: #6f7886; font-size: 15px; line-height: 1.9; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 28px; }.button-arrow { margin-left: 7px; }
.hero-orb { position: absolute; z-index: 1; border-radius: 50%; filter: blur(1px); animation: orb-drift 8s ease-in-out infinite; }.hero-orb--sky { width: 200px; height: 200px; right: 24%; top: -86px; background: rgba(121,205,237,.3); }.hero-orb--rose { width: 170px; height: 170px; right: -45px; bottom: -52px; background: rgba(236,114,150,.22); animation-delay: -3s; }
.hero-pixels { position: absolute; z-index: 1; inset: 0; opacity: .55; }.hero-pixels i { position: absolute; width: 11px; height: 11px; border-radius: 3px; background: rgba(236,114,150,.34); animation: pixel-float 5s ease-in-out infinite; }.hero-pixels i:nth-child(1) { left: 4%; top: 19%; }.hero-pixels i:nth-child(2) { left: 9%; bottom: 11%; background: rgba(104,205,181,.5); animation-delay: -1s; }.hero-pixels i:nth-child(3) { left: 42%; top: 14%; background: rgba(155,137,223,.4); animation-delay: -2s; }.hero-pixels i:nth-child(4) { right: 42%; bottom: 15%; width: 7px; height: 7px; }.hero-pixels i:nth-child(5) { right: 6%; top: 13%; background: rgba(98,196,233,.45); }.hero-pixels i:nth-child(6) { right: 12%; bottom: 13%; animation-delay: -2.4s; }.hero-pixels i:nth-child(n+7) { display: none; }
.team-hero__visual { position: relative; z-index: 3; display: grid; place-items: center; align-content: center; }.visual-card { width: min(360px, 92%); padding: 25px 27px; border: 1px solid rgba(255,255,255,.86); border-radius: 25px; background: rgba(255,255,255,.72); box-shadow: 0 24px 55px rgba(78,89,116,.13); backdrop-filter: blur(16px); transform: rotate(2.5deg); transition: transform .4s cubic-bezier(.22,1,.36,1); }.team-hero:hover .visual-card { transform: rotate(0) translateY(-5px); }
.visual-card__top { display: flex; align-items: center; justify-content: space-between; color: #717a88; font-size: 13px; font-weight: 700; }.visual-card__top i { width: 8px; height: 8px; border-radius: 50%; background: #68cdb5; box-shadow: 0 0 0 6px rgba(104,205,181,.15); }.visual-card > strong { display: block; margin-top: 18px; color: #1e232b; font-size: 46px; line-height: 1; font-weight: 900; }.visual-card > small { display: block; margin-top: 9px; color: #929aa5; }
.visual-wave { display: flex; align-items: flex-end; gap: 7px; height: 54px; margin-top: 22px; }.visual-wave i { flex: 1; min-width: 10px; border-radius: 8px 8px 3px 3px; background: linear-gradient(180deg, #ef86a5, #afdff1); animation: wave-grow 1.1s cubic-bezier(.22,1,.36,1) both; }.visual-wave i:nth-child(1) { height: 28%; }.visual-wave i:nth-child(2) { height: 44%; animation-delay: 80ms; }.visual-wave i:nth-child(3) { height: 67%; animation-delay: 160ms; }.visual-wave i:nth-child(4) { height: 52%; animation-delay: 240ms; }.visual-wave i:nth-child(5) { height: 82%; animation-delay: 320ms; }.visual-wave i:nth-child(6) { height: 100%; animation-delay: 400ms; }
.member-stack { position: absolute; z-index: 2; top: 17px; left: 2%; display: flex; }.member-avatar { display: grid; place-items: center; width: 42px; height: 42px; margin-left: -9px; border: 3px solid rgba(255,255,255,.9); border-radius: 50%; color: #fff; font-size: 12px; font-weight: 800; box-shadow: 0 7px 18px rgba(60,69,89,.13); }.member-avatar:first-child { margin-left: 0; }.member-avatar--rose { background: #ed83a2; }.member-avatar--sky { background: #70c4e5; }.member-avatar--mint { background: #64c9b2; }.member-avatar--more { color: #716a8d; background: #e7e1fb; }
.owner-alert { margin-bottom: 18px; border-radius: 16px; }.stat-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }.team-workspace { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(290px, .55fr); gap: 18px; align-items: start; }
.team-panel, .side-panel { border: 1px solid rgba(225,229,237,.86); background: rgba(255,255,255,.86); box-shadow: 0 15px 42px rgba(44,49,63,.07); backdrop-filter: blur(16px); }.team-panel { min-width: 0; padding: clamp(20px, 2.7vw, 34px); border-radius: 26px; }.panel-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; margin-bottom: 24px; }.panel-kicker, .side-panel__heading small { color: #b06a82; font-size: 10px; font-weight: 900; letter-spacing: 1.7px; }.panel-header h2 { margin: 6px 0 0; color: #1b2027; font-size: 25px; }.panel-header p { margin: 7px 0 0; color: #929aa5; font-size: 13px; }
.role-summary { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 12px; color: #7f8895; font-size: 12px; }.role-summary span { display: flex; align-items: center; gap: 6px; }.role-summary i { width: 7px; height: 7px; border-radius: 50%; }.role-summary i.is-admin { background: #ec9a72; }.role-summary i.is-editor { background: #68cdb5; }.role-summary i.is-viewer { background: #9b89df; }
.team-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; min-height: 160px; }.team-card { --role-accent: #9b89df; position: relative; display: block; width: 100%; padding: 21px; overflow: hidden; border: 1px solid #eceef3; border-radius: 21px; background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(249,250,253,.95)); color: inherit; text-align: left; cursor: pointer; box-shadow: 0 8px 22px rgba(39,44,57,.045); animation: card-in .65s var(--card-delay, 0ms) cubic-bezier(.22,1,.36,1) both; transition: transform .34s cubic-bezier(.22,1,.36,1), box-shadow .34s ease, border-color .34s ease; }.team-card.is-admin { --role-accent: #ec9a72; }.team-card.is-editor { --role-accent: #68cdb5; }.team-card.is-viewer { --role-accent: #9b89df; }.team-card:hover { transform: translateY(-7px); border-color: color-mix(in srgb, var(--role-accent) 35%, #e7e9ef); box-shadow: 0 20px 42px color-mix(in srgb, var(--role-accent) 15%, transparent); }
.team-card__glow { position: absolute; width: 150px; height: 150px; right: -84px; top: -88px; border-radius: 50%; background: radial-gradient(circle, color-mix(in srgb, var(--role-accent) 28%, transparent), transparent 69%); transition: transform .4s ease; }.team-card:hover .team-card__glow { transform: scale(1.45); }.team-card__top, .team-card__identity { position: relative; z-index: 1; display: flex; align-items: center; }.team-card__top { justify-content: space-between; gap: 12px; }.team-card__identity { min-width: 0; gap: 12px; }.team-card__avatar { flex: 0 0 auto; display: grid; place-items: center; width: 46px; height: 46px; border-radius: 15px; color: #fff; background: linear-gradient(135deg, color-mix(in srgb, var(--role-accent) 76%, #fff), var(--role-accent)); font-size: 18px; font-weight: 900; box-shadow: 8px 8px 0 color-mix(in srgb, var(--role-accent) 12%, transparent); }.team-card__identity > span:last-child { min-width: 0; }.team-card__identity strong { display: block; overflow: hidden; color: #22262d; font-size: 16px; text-overflow: ellipsis; white-space: nowrap; }.team-card__identity small { display: block; margin-top: 5px; color: #a0a7b1; font-size: 11px; }
.team-card__metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 23px; }.team-card__metrics > span { padding: 12px; border-radius: 14px; background: #f7f8fb; }.team-card__metrics small { display: block; color: #979faa; font-size: 11px; }.team-card__metrics strong { display: block; margin-top: 6px; color: #30353d; font-size: 15px; }.team-card__metrics em { color: #929aa5; font-size: 11px; font-style: normal; font-weight: 600; }.team-card__quota { margin-top: 17px; }.team-card__quota > div { display: flex; justify-content: space-between; margin-bottom: 8px; color: #8f97a2; font-size: 11px; }.team-card__quota strong { color: var(--role-accent); }.team-card__footer { display: flex; justify-content: space-between; gap: 10px; margin-top: 15px; color: #9ca3ad; font-size: 11px; }.team-card__footer span:last-child { display: flex; align-items: center; gap: 4px; color: var(--role-accent); font-weight: 800; }
.empty-team { display: grid; justify-items: center; padding: 54px 20px 42px; text-align: center; }.empty-team h3 { margin: 18px 0 0; color: #252a31; }.empty-team p { margin: 8px 0 20px; color: #929aa5; font-size: 13px; }.empty-team__pixels { display: grid; grid-template-columns: repeat(3, 18px); gap: 5px; transform: rotate(8deg); }.empty-team__pixels i { width: 18px; height: 18px; border-radius: 5px; background: #f2a0b9; }.empty-team__pixels i:nth-child(2), .empty-team__pixels i:nth-child(4) { background: #9fdcf4; }.empty-team__pixels i:nth-child(3) { background: #dcd4f7; }.empty-team__pixels i:nth-child(5) { background: #bfeadf; }
.team-side { display: grid; gap: 16px; }.side-panel { padding: 22px; border-radius: 22px; }.side-panel__heading { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }.side-panel__heading.compact { margin-bottom: 12px; }.side-panel__heading h3 { margin: 4px 0 0; color: #272c34; font-size: 15px; }.side-icon { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 14px; color: #d06182; background: #fff0f5; }.side-icon--sky { color: #4ca8ce; background: #eaf9ff; }.owner-panel { background: linear-gradient(145deg, rgba(255,255,255,.94), rgba(255,241,245,.72)); }.owned-team-name { color: #23272f; font-size: 20px; font-weight: 900; }.owner-panel p { margin: 9px 0 17px; color: #89929e; font-size: 12px; line-height: 1.7; }
.recent-list { display: grid; gap: 7px; }.recent-list button { display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 10px; width: 100%; padding: 9px; border: 0; border-radius: 13px; background: transparent; text-align: left; cursor: pointer; transition: background .2s ease, transform .2s ease; }.recent-list button:hover { background: #f7f8fb; transform: translateX(3px); }.recent-avatar { display: grid; place-items: center; width: 35px; height: 35px; border-radius: 11px; color: #786f99; background: #efebff; font-weight: 900; }.recent-list strong, .recent-list small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.recent-list strong { color: #343940; font-size: 12px; }.recent-list small { margin-top: 4px; color: #9ba2ac; font-size: 10px; }.recent-list .el-icon { color: #b0b6bf; }.side-empty { margin: 0; color: #99a1ac; font-size: 12px; line-height: 1.7; }
.guide-panel { color: #fff; background: linear-gradient(145deg, #6d789a, #927797 62%, #c57c96); }.guide-badge { display: inline-flex; padding: 5px 9px; border-radius: 999px; background: rgba(255,255,255,.16); font-size: 10px; font-weight: 800; }.guide-panel h3 { margin: 13px 0 16px; font-size: 17px; }.guide-panel ul { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }.guide-panel li { display: flex; align-items: center; gap: 10px; color: rgba(255,255,255,.82); font-size: 12px; }.guide-panel li span { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 9px; background: rgba(255,255,255,.13); color: #fff; font-size: 9px; font-weight: 800; }
@keyframes orb-drift { 0%,100% { transform: translate3d(0,0,0); } 50% { transform: translate3d(14px,-12px,0); } } @keyframes pixel-float { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-9px) rotate(9deg); } } @keyframes wave-grow { from { transform: scaleY(.1); transform-origin: bottom; opacity: 0; } to { transform: scaleY(1); transform-origin: bottom; opacity: 1; } } @keyframes card-in { from { transform: translateY(15px); opacity: 0; } }
@media (max-width: 1120px) { .team-hero { grid-template-columns: minmax(0,1fr) 340px; }.team-workspace { grid-template-columns: 1fr; }.team-side { grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 900px) { .team-hero { grid-template-columns: 1fr; min-height: auto; }.team-hero__visual { display: none; }.stat-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }.team-side { grid-template-columns: 1fr 1fr; }.guide-panel { grid-column: 1 / -1; } }
@media (max-width: 650px) { .team-hero { padding: 28px 22px; border-radius: 24px; }.team-hero h1 { font-size: 36px; letter-spacing: -1.4px; }.hero-actions .el-button { width: 100%; margin-left: 0; }.stat-grid, .team-grid, .team-side { grid-template-columns: 1fr; }.guide-panel { grid-column: auto; }.panel-header { align-items: flex-start; flex-direction: column; }.role-summary { justify-content: flex-start; }.team-card__metrics { grid-template-columns: 1fr; }.team-card__footer { align-items: flex-start; flex-direction: column; } }
@media (prefers-reduced-motion: reduce) { .hero-orb, .hero-pixels i, .visual-wave i, .team-card { animation: none; }.visual-card, .team-card, .team-card__glow, .recent-list button { transition: none; }.team-hero:hover .visual-card, .team-card:hover, .recent-list button:hover { transform: none; } }
</style>
