<script setup lang="ts">
/** 我的空间首页：空间资产、配额状态、功能入口与最近上传。 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Box, Coin, Medal, PictureFilled } from '@element-plus/icons-vue'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import { formatBytes, spaceLevelLabel, type SpaceInfoRead } from '@/types/space'
import type { PictureListItemRead } from '@/types/picture'
import PictureCard from '@/components/PictureCard.vue'
import StatCard from '@/components/StatCard.vue'
import SpaceLevelDialog from './SpaceLevelDialog.vue'

const router = useRouter()
const loading = ref(false)
const notFound = ref(false)
const loadError = ref('')
const space = ref<SpaceInfoRead | null>(null)
const recent = ref<PictureListItemRead[]>([])
const levelVisible = ref(false)

const createdLabel = computed(() => {
  if (!space.value?.created_at) return '暂无记录'
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(space.value.created_at))
})

const healthStatus = computed(() => {
  if (!space.value) return { label: '加载中', tone: 'normal' }
  if (space.value.status === 'banned') return { label: '空间已封禁', tone: 'danger' }
  if (space.value.remaining_size < 0 || space.value.remaining_count < 0) return { label: '配额已超限', tone: 'danger' }
  if (capacityPercent() >= 80 || countPercent() >= 80) return { label: '配额即将用尽', tone: 'warning' }
  return { label: '空间运行良好', tone: 'normal' }
})

const spaceActions = [
  { title: '空间图册', desc: '浏览和管理私藏素材', icon: 'PictureFilled', path: '/spaces/gallery', tone: 'rose' },
  { title: '颜色搜图', desc: '通过主色调发现图片', icon: 'Brush', path: '/spaces/color-search', tone: 'sky' },
  { title: '数据分析', desc: '查看容量与上传趋势', icon: 'DataAnalysis', path: '/analytics/my-space', tone: 'lavender' },
] as const

function capacityPercent(): number {
  if (!space.value || space.value.max_size <= 0) return 0
  return Math.min(100, Math.round((space.value.total_size / space.value.max_size) * 100))
}

function countPercent(): number {
  if (!space.value || space.value.max_count <= 0) return 0
  return Math.min(100, Math.round((space.value.total_count / space.value.max_count) * 100))
}

async function load() {
  loading.value = true
  notFound.value = false
  loadError.value = ''
  recent.value = []
  space.value = null
  try {
    space.value = await spaceApi.getMy()
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) notFound.value = true
    else {
      loadError.value = getErrorMessage(err, '获取空间信息失败')
      ElMessage.error(loadError.value)
    }
  } finally {
    loading.value = false
  }

  if (space.value) {
    try {
      const response = await spaceApi.listPictures({ page: 1, items_per_page: 8, sort: 'time' })
      recent.value = response.data
    } catch {
      recent.value = []
    }
  }
}

onMounted(load)
</script>

<template>
  <main class="space-page page-container">
    <span class="space-orb space-orb--blue" aria-hidden="true"></span>
    <span class="space-orb space-orb--pink" aria-hidden="true"></span>

    <el-skeleton v-if="loading" :rows="8" animated />

    <section v-else-if="notFound" class="space-state analytics-reveal">
      <div class="state-art" aria-hidden="true">
        <span><el-icon><FolderAdd /></el-icon></span><i></i><i></i><i></i>
      </div>
      <div class="state-kicker">PRIVATE SPACE · 私人工作台</div>
      <h1>创建属于你的灵感空间</h1>
      <p>私有空间与公共图库隔离存储，让收藏、创作素材和个人灵感保持井然有序。</p>
      <el-button type="primary" size="large" @click="router.push('/spaces/create')">
        <el-icon><Plus /></el-icon>创建空间
      </el-button>
    </section>

    <section v-else-if="loadError" class="space-state analytics-reveal">
      <div class="state-art state-art--error"><span><el-icon><Warning /></el-icon></span></div>
      <h1>空间暂时无法抵达</h1>
      <p>{{ loadError }}</p>
      <el-button type="primary" size="large" @click="load">重新加载</el-button>
    </section>

    <template v-else-if="space">
      <section class="space-hero analytics-reveal">
        <div class="space-hero__texture" aria-hidden="true">
          <i v-for="index in 22" :key="index"></i>
        </div>
        <div class="space-hero__main">
          <div class="space-symbol"><el-icon><FolderOpened /></el-icon><span></span></div>
          <div class="space-identity">
            <div class="space-kicker">PRIVATE SPACE · 私人工作台</div>
            <div class="space-name-row">
              <h1>{{ space.name }}</h1>
              <el-tag size="small" effect="dark">{{ spaceLevelLabel(space.space_level) }}</el-tag>
              <el-tag v-if="space.status === 'banned'" size="small" type="danger" effect="dark">已封禁</el-tag>
            </div>
            <p>空间 ID {{ space.id }} · 创建于 {{ createdLabel }}</p>
            <span class="health-pill" :class="`health-pill--${healthStatus.tone}`"><i></i>{{ healthStatus.label }}</span>
          </div>
        </div>
        <div class="space-hero__actions">
          <el-button size="large" @click="levelVisible = true"><el-icon><Setting /></el-icon>调整等级</el-button>
          <el-button type="primary" size="large" @click="router.push('/spaces/gallery')"><el-icon><Right /></el-icon>进入空间</el-button>
        </div>
      </section>

      <section class="space-stat-grid" aria-label="空间概览">
        <StatCard label="图片数量" :value="space.total_count" :hint="`/ ${space.max_count}`" description="已保存在当前空间" :icon="PictureFilled" :delay="80" />
        <StatCard label="已用容量" :value="formatBytes(space.total_size)" description="当前空间累计存储" :icon="Coin" accent="sky" :delay="140" />
        <StatCard label="剩余容量" :value="formatBytes(Math.max(0, space.remaining_size))" description="还能继续使用的容量" :icon="Box" accent="mint" :delay="200" />
        <StatCard label="空间等级" :value="spaceLevelLabel(space.space_level)" description="决定容量与图片配额" :icon="Medal" accent="lavender" :delay="260" />
      </section>

      <section class="space-dashboard-grid">
        <article class="space-panel quota-panel analytics-reveal" style="--reveal-delay: 320ms">
          <header class="space-panel__head">
            <div><div class="panel-index">01 · QUOTA</div><h2>空间配额</h2><p>实时了解容量与图片数量使用情况</p></div>
            <span class="quota-total">{{ Math.max(capacityPercent(), countPercent()) }}% 峰值</span>
          </header>
          <div class="quota-list">
            <div class="quota-item">
              <div class="quota-title"><span><i class="quota-dot quota-dot--rose"></i>容量使用</span><strong>{{ capacityPercent() }}%</strong></div>
              <el-progress :percentage="capacityPercent()" :show-text="false" :stroke-width="12" :status="space.remaining_size < 0 ? 'exception' : undefined" />
              <div class="quota-meta"><span>{{ formatBytes(space.total_size) }} / {{ formatBytes(space.max_size) }}</span><b v-if="space.remaining_size < 0" class="over">已超限</b><b v-else>剩余 {{ formatBytes(space.remaining_size) }}</b></div>
            </div>
            <div class="quota-item">
              <div class="quota-title"><span><i class="quota-dot quota-dot--blue"></i>图片数量</span><strong>{{ countPercent() }}%</strong></div>
              <el-progress :percentage="countPercent()" :show-text="false" :stroke-width="12" :status="space.remaining_count < 0 ? 'exception' : undefined" />
              <div class="quota-meta"><span>{{ space.total_count }} / {{ space.max_count }} 张</span><b v-if="space.remaining_count < 0" class="over">已超限</b><b v-else>剩余 {{ space.remaining_count }} 张</b></div>
            </div>
          </div>
        </article>

        <article class="space-panel action-panel analytics-reveal" style="--reveal-delay: 380ms">
          <header class="space-panel__head"><div><div class="panel-index">02 · WORKSPACE</div><h2>创作工具</h2><p>从素材管理到灵感分析</p></div></header>
          <div class="space-action-list">
            <button v-for="item in spaceActions" :key="item.path" @click="router.push(item.path)">
              <span class="action-icon" :class="`action-icon--${item.tone}`"><el-icon><component :is="item.icon" /></el-icon></span>
              <span><strong>{{ item.title }}</strong><small>{{ item.desc }}</small></span>
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </article>
      </section>

      <section class="recent-panel analytics-reveal" style="--reveal-delay: 440ms">
        <header class="recent-head">
          <div><div class="panel-index">03 · RECENT UPLOADS</div><h2>最近上传</h2><p>继续整理最近加入空间的素材</p></div>
          <el-button @click="router.push('/spaces/gallery')">查看全部 <el-icon><ArrowRight /></el-icon></el-button>
        </header>
        <div v-if="recent.length" class="masonry recent-masonry">
          <PictureCard v-for="item in recent" :key="item.id" :item="item" kind="space" />
        </div>
        <div v-else class="recent-empty">
          <span><el-icon><Picture /></el-icon></span>
          <h3>空间里还没有图片</h3>
          <p>进入空间上传第一张图片，开始建立你的私人素材库。</p>
          <el-button type="primary" @click="router.push('/spaces/gallery')">进入空间图册</el-button>
        </div>
      </section>
    </template>

    <SpaceLevelDialog v-model="levelVisible" :current-level="space?.space_level ?? 0" @success="load" />
  </main>
</template>

<style scoped>
.space-page { position: relative; isolation: isolate; min-height: calc(100vh - 72px); overflow: hidden; padding-bottom: 70px; }
.space-page::before { content: ''; position: absolute; z-index: -2; inset: 0 0 auto; height: 600px; background: radial-gradient(circle at 7% 8%,rgba(159,220,244,.35),transparent 31%),radial-gradient(circle at 92% 4%,rgba(249,175,197,.29),transparent 29%); pointer-events: none; }
.space-orb { position: absolute; z-index: -1; border-radius: 50%; pointer-events: none; animation: space-drift 8s ease-in-out infinite alternate; }
.space-orb--blue { width: 220px; height: 220px; left: -120px; top: 760px; background: rgba(159,220,244,.18); }
.space-orb--pink { width: 300px; height: 300px; right: -160px; top: 1100px; background: rgba(236,114,150,.13); animation-delay: -3s; }

.space-state { position: relative; z-index: 1; min-height: 620px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 56px 24px; overflow: hidden; border: 1px solid rgba(255,255,255,.85); border-radius: 32px; background: linear-gradient(135deg,rgba(229,247,253,.9),rgba(255,255,255,.92) 50%,rgba(255,232,239,.9)); box-shadow: 0 28px 72px rgba(39,45,58,.1); text-align: center; }
.state-art { position: relative; width: 160px; height: 130px; display: grid; place-items: center; }
.state-art span { position: relative; z-index: 1; width: 92px; height: 92px; display: grid; place-items: center; border-radius: 30px 10px 30px 10px; color: #fff; background: linear-gradient(145deg,#75cce9,#ed789a); box-shadow: 17px 17px 0 rgba(236,114,150,.13); font-size: 38px; animation: state-float 3.6s ease-in-out infinite; }
.state-art i { position: absolute; width: 20px; height: 20px; border-radius: 7px; background: #e981a0; animation: state-pixel 3s ease-in-out infinite alternate; }
.state-art i:nth-child(2) { left: 4px; top: 12px; background: #7acfea; }
.state-art i:nth-child(3) { right: 0; top: 34px; background: #8bd5c3; animation-delay: -.8s; }
.state-art i:nth-child(4) { left: 20px; bottom: 2px; background: #aa9ce5; animation-delay: -1.4s; }
.state-art--error span { background: linear-gradient(145deg,#efad77,#e76b7f); }
.state-kicker { margin-top: 24px; color: #a9677b; font-size: 10px; font-weight: 900; letter-spacing: 2px; }
.space-state h1 { margin: 12px 0 0; color: #1d2128; font-size: clamp(35px,5vw,58px); line-height: 1.1; font-weight: 950; letter-spacing: -2.5px; }
.space-state p { max-width: 580px; margin: 15px auto 26px; color: #7f8995; font-size: 14px; line-height: 1.85; }
.space-state .el-button { min-width: 142px; height: 46px; }

.space-hero { position: relative; z-index: 1; min-height: 295px; display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; margin-bottom: 18px; padding: 46px clamp(28px,5vw,62px); overflow: hidden; border: 1px solid rgba(255,255,255,.86); border-radius: 31px; background: linear-gradient(125deg,rgba(212,241,251,.94),rgba(255,255,255,.94) 50%,rgba(255,226,235,.93)); box-shadow: 0 26px 68px rgba(41,46,58,.1); }
.space-hero::before { content: ''; position: absolute; width: 390px; height: 390px; right: -120px; top: -250px; border-radius: 50%; border: 68px solid rgba(255,255,255,.26); }
.space-hero__texture { position: absolute; inset: 0 0 0 58%; display: grid; grid-template-columns: repeat(6,10px); align-content: center; justify-content: center; gap: 18px; opacity: .38; transform: rotate(-9deg); }
.space-hero__texture i { width: 10px; height: 10px; border-radius: 3px; background: #e17a9a; animation: texture-float 2.8s ease-in-out infinite alternate; }
.space-hero__texture i:nth-child(3n) { background: #75cce9; animation-delay: -.7s; }
.space-hero__texture i:nth-child(4n) { background: #8bd5c3; animation-delay: -1.3s; }
.space-hero__main { position: relative; z-index: 1; display: flex; align-items: center; gap: 22px; min-width: 0; }
.space-symbol { position: relative; width: 88px; height: 88px; display: grid; place-items: center; flex-shrink: 0; border: 7px solid rgba(255,255,255,.82); border-radius: 29px 10px 29px 10px; color: #fff; background: linear-gradient(145deg,#72cbea,#ec7296); box-shadow: 14px 17px 0 rgba(236,114,150,.12); font-size: 37px; }
.space-symbol span { position: absolute; right: -5px; bottom: -5px; width: 20px; height: 20px; border: 5px solid #fff; border-radius: 50%; background: #59c3a7; }
.space-kicker { margin-bottom: 8px; color: #a9677b; font-size: 10px; font-weight: 900; letter-spacing: 2px; }
.space-name-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.space-name-row h1 { margin: 0; color: #1d2128; font-size: clamp(34px,4.5vw,54px); line-height: 1.08; font-weight: 950; letter-spacing: -2.5px; }
.space-identity > p { margin: 8px 0 0; color: #77818e; font-size: 12px; font-weight: 700; }
.health-pill { display: inline-flex; align-items: center; gap: 7px; margin-top: 15px; padding: 6px 10px; border-radius: 999px; color: #378c75; background: rgba(234,248,244,.86); font-size: 11px; font-weight: 800; }
.health-pill i { width: 7px; height: 7px; border-radius: 50%; background: #51b99d; box-shadow: 0 0 0 5px rgba(81,185,157,.12); }
.health-pill--warning { color: #a97627; background: rgba(255,246,224,.88); }
.health-pill--warning i { background: #e6ab4b; box-shadow: 0 0 0 5px rgba(230,171,75,.14); }
.health-pill--danger { color: #b54e61; background: rgba(255,235,239,.9); }
.health-pill--danger i { background: #e56b7f; box-shadow: 0 0 0 5px rgba(229,107,127,.14); }
.space-hero__actions { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 10px; }
.space-hero__actions .el-button { height: 44px; }
.space-hero__actions .el-button:not(.el-button--primary) { background: rgba(255,255,255,.72); backdrop-filter: blur(10px); }

.space-stat-grid { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 16px; margin-bottom: 18px; }
.space-dashboard-grid { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(0,1.35fr) minmax(330px,.65fr); gap: 18px; margin-bottom: 18px; }
.space-panel,.recent-panel { min-width: 0; padding: 24px; border: 1px solid rgba(224,228,236,.92); border-radius: 24px; background: rgba(255,255,255,.9); box-shadow: 0 14px 38px rgba(39,45,58,.065); backdrop-filter: blur(16px); transition: transform .3s ease,box-shadow .3s ease; }
.space-panel:hover,.recent-panel:hover { transform: translateY(-4px); box-shadow: 0 23px 52px rgba(39,45,58,.1); }
.space-panel__head,.recent-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; margin-bottom: 22px; }
.panel-index { margin-bottom: 7px; color: #cf7993; font-size: 9px; font-weight: 900; letter-spacing: 1.4px; }
.space-panel__head h2,.recent-head h2 { margin: 0; color: #292e37; font-size: 19px; font-weight: 900; }
.space-panel__head p,.recent-head p { margin: 6px 0 0; color: #9ba3ae; font-size: 11px; }
.quota-total { padding: 6px 10px; border-radius: 999px; color: #6f7884; background: #f5f7fa; font-size: 10px; font-weight: 800; }
.quota-list { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }
.quota-item { padding: 19px; border: 1px solid #eef0f4; border-radius: 18px; background: linear-gradient(145deg,#fbfcfe,#fff); }
.quota-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 14px; }
.quota-title span { display: inline-flex; align-items: center; gap: 8px; color: #68727f; font-size: 12px; font-weight: 800; }
.quota-title strong { color: #252a32; font-size: 21px; font-weight: 950; }
.quota-dot { width: 8px; height: 8px; border-radius: 50%; background: #ec7296; box-shadow: 0 0 0 5px rgba(236,114,150,.12); }
.quota-dot--blue { background: #70cae9; box-shadow: 0 0 0 5px rgba(112,202,233,.13); }
.quota-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 10px; color: #9aa2ad; font-size: 10px; }
.quota-meta b { color: #65707c; font-weight: 800; }
.quota-meta b.over { color: #e36476; }
.space-action-list { display: grid; gap: 9px; }
.space-action-list button { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px; border: 1px solid transparent; border-radius: 16px; color: #737d89; background: #fafbfd; text-align: left; cursor: pointer; transition: transform .24s ease,border-color .24s ease,background .24s ease; }
.space-action-list button:hover { transform: translateX(5px); border-color: #f1d1db; background: #fff8fa; }
.action-icon { width: 42px; height: 42px; display: grid; place-items: center; flex-shrink: 0; border-radius: 14px; color: #db6488; background: #fff0f5; }
.action-icon--sky { color: #55badf; background: #eaf9ff; }
.action-icon--lavender { color: #8e7bd3; background: #f1edff; }
.space-action-list button > span:nth-child(2) { min-width: 0; flex: 1; }
.space-action-list strong,.space-action-list small { display: block; }
.space-action-list strong { color: #3b414b; font-size: 13px; font-weight: 800; }
.space-action-list small { margin-top: 4px; color: #a0a8b3; font-size: 10px; }
.recent-panel { position: relative; z-index: 1; }
.recent-head { align-items: flex-end; }
.recent-head .el-button { flex-shrink: 0; }
.recent-masonry { margin-top: 4px; }
.recent-empty { min-height: 260px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 30px; text-align: center; }
.recent-empty > span { width: 62px; height: 62px; display: grid; place-items: center; border-radius: 22px 8px 22px 8px; color: #fff; background: linear-gradient(145deg,#75cce9,#ec7296); box-shadow: 11px 11px 0 rgba(236,114,150,.12); font-size: 25px; }
.recent-empty h3 { margin: 22px 0 0; color: #383e48; font-size: 17px; font-weight: 900; }
.recent-empty p { margin: 8px 0 18px; color: #9aa3ae; font-size: 12px; }

@keyframes space-drift { to { transform: translate(34px,-25px) scale(1.1); } }
@keyframes texture-float { to { transform: translateY(-8px) rotate(8deg); opacity: .55; } }
@keyframes state-float { 50% { transform: translateY(-10px) rotate(2deg); } }
@keyframes state-pixel { to { transform: translateY(-10px) rotate(12deg); } }
@media (max-width: 1080px) {
  .space-stat-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .space-dashboard-grid { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .space-page { min-height: calc(100vh - 108px); padding-left: 16px; padding-right: 16px; }
  .space-state { min-height: 430px; padding: 42px 18px; border-radius: 25px; }
  .space-hero { align-items: flex-start; flex-direction: column; padding: 32px 24px; }
  .space-hero__main { align-items: flex-start; flex-direction: column; }
  .space-hero__actions { width: 100%; }
  .space-hero__actions .el-button { flex: 1 1 140px; margin-left: 0; }
  .space-stat-grid,.quota-list { grid-template-columns: 1fr; }
  .space-panel,.recent-panel { padding: 20px 16px; }
  .recent-head { align-items: flex-start; flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  .space-orb,.space-hero__texture i,.state-art span,.state-art i { animation: none; }
  .space-panel,.recent-panel,.space-action-list button { transition: none; }
  .space-panel:hover,.recent-panel:hover,.space-action-list button:hover { transform: none; }
}
</style>
