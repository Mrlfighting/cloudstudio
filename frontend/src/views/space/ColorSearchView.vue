<script setup lang="ts">
/** 私有空间颜色搜图：选择目标颜色，按主色距离检索自己的空间图片。 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { ColorSearchItem, SpaceInfoRead } from '@/types/space'
import PictureCard from '@/components/PictureCard.vue'

const router = useRouter()
const loading = ref(true)
const searching = ref(false)
const notFound = ref(false)
const loadError = ref('')
const searched = ref(false)
const color = ref('#ec7296')
const space = ref<SpaceInfoRead | null>(null)
const rows = ref<ColorSearchItem[]>([])

const presets = [
  { name: '珊瑚粉', value: '#ec7296' },
  { name: '天空蓝', value: '#70cae9' },
  { name: '薄荷绿', value: '#69cbb5' },
  { name: '薰衣草', value: '#a99be6' },
  { name: '暖阳橙', value: '#f3bd72' },
  { name: '深夜蓝', value: '#34445f' },
] as const

const colorStyle = computed(() => ({ '--active-color': color.value }))

async function loadSpace() {
  loading.value = true
  notFound.value = false
  loadError.value = ''
  try {
    space.value = await spaceApi.getMy()
  } catch (err) {
    space.value = null
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) notFound.value = true
    else loadError.value = getErrorMessage(err, '获取私有空间失败')
  } finally {
    loading.value = false
  }
}

async function search() {
  if (!space.value || !color.value) return
  searching.value = true
  searched.value = false
  try {
    const result = await spaceApi.searchByColor({ color: color.value, limit: 50 })
    rows.value = [...result].sort((a, b) => a.color_distance - b.color_distance)
    searched.value = true
  } catch (err) {
    rows.value = []
    ElMessage.error(getErrorMessage(err, '按颜色搜索失败'))
  } finally {
    searching.value = false
  }
}

function applyPreset(value: string): void {
  color.value = value
}

function formatDistance(distance: number): string {
  return Number.isInteger(distance) ? String(distance) : distance.toFixed(2)
}

onMounted(loadSpace)
</script>

<template>
  <main class="color-page page-container" :style="colorStyle">
    <span class="color-orb color-orb--one" aria-hidden="true"></span>
    <span class="color-orb color-orb--two" aria-hidden="true"></span>

    <header class="color-hero analytics-reveal">
      <div class="color-hero__copy">
        <div class="color-eyebrow"><span></span> COLOR SEARCH · 私有空间</div>
        <h1>让颜色带你找到灵感</h1>
        <p>选择一种色彩，从你的私有空间中寻找主色调最接近的图片。</p>
        <div class="color-hero__actions">
          <el-button @click="router.push('/spaces')"><el-icon><Back /></el-icon>我的空间</el-button>
          <el-button @click="router.push('/spaces/gallery')"><el-icon><Picture /></el-icon>空间图册</el-button>
        </div>
      </div>
      <div class="color-hero__visual" aria-hidden="true">
        <span class="color-ring color-ring--outer"></span>
        <span class="color-ring color-ring--middle"></span>
        <span class="color-core"><i></i></span>
        <b>{{ color.toUpperCase() }}</b>
      </div>
    </header>

    <el-skeleton v-if="loading" class="color-skeleton" :rows="6" animated />

    <section v-else-if="notFound" class="color-state analytics-reveal">
      <div class="state-icon"><el-icon><FolderAdd /></el-icon></div>
      <h2>先创建一个私有空间</h2>
      <p>颜色搜图只检索你的私有空间图片。创建空间并上传素材后，即可按主色调发现内容。</p>
      <el-button type="primary" size="large" @click="router.push('/spaces/create')">创建私有空间</el-button>
    </section>

    <section v-else-if="loadError" class="color-state analytics-reveal">
      <div class="state-icon state-icon--error"><el-icon><Warning /></el-icon></div>
      <h2>暂时无法加载空间</h2>
      <p>{{ loadError }}</p>
      <el-button type="primary" size="large" @click="loadSpace">重新加载</el-button>
    </section>

    <template v-else-if="space">
      <section class="color-workbench analytics-reveal" style="--reveal-delay: 100ms">
        <div class="color-preview">
          <span class="preview-glow"></span>
          <div class="preview-swatch">
            <span></span>
            <strong>{{ color.toUpperCase() }}</strong>
          </div>
          <div class="space-chip"><el-icon><Lock /></el-icon>{{ space.name }}</div>
        </div>

        <div class="color-controls">
          <div class="workbench-heading">
            <div><span>01</span><h2>选择目标颜色</h2></div>
            <p>你可以使用取色器、输入 HEX 色值，或从推荐色板中快速选择。</p>
          </div>

          <div class="preset-list" aria-label="推荐颜色">
            <button
              v-for="preset in presets"
              :key="preset.value"
              :class="{ active: color.toLowerCase() === preset.value.toLowerCase() }"
              :title="`${preset.name} ${preset.value}`"
              @click="applyPreset(preset.value)"
            >
              <i :style="{ background: preset.value }"></i>
              <span>{{ preset.name }}</span>
            </button>
          </div>

          <div class="color-input-row">
            <el-color-picker v-model="color" size="large" aria-label="打开颜色选择器" />
            <el-input v-model="color" maxlength="7" aria-label="目标颜色 HEX 值">
              <template #prefix><span class="hex-mark">HEX</span></template>
            </el-input>
            <el-button type="primary" size="large" :loading="searching" @click="search">
              <el-icon><Search /></el-icon>搜索相近图片
            </el-button>
          </div>
          <div class="search-note"><el-icon><InfoFilled /></el-icon>结果按颜色距离由近到远排列，最多显示 50 张。</div>
        </div>
      </section>

      <section class="color-results analytics-reveal" style="--reveal-delay: 180ms">
        <header class="results-head">
          <div>
            <div class="results-kicker">02 · SEARCH RESULTS</div>
            <h2>{{ searched ? '匹配结果' : '等待探索' }}</h2>
            <p>{{ searched ? `找到 ${rows.length} 张与 ${color.toUpperCase()} 相近的图片` : '选择颜色后开始探索你的空间素材' }}</p>
          </div>
          <span v-if="searched" class="result-count"><i></i>{{ rows.length }} 张</span>
        </header>

        <div v-loading="searching" class="results-grid">
          <div v-for="item in rows" :key="item.id" class="color-item">
            <PictureCard :item="item" kind="space" />
            <span class="distance"><i></i>色差 {{ formatDistance(item.color_distance) }}</span>
          </div>
        </div>

        <div v-if="!searching && searched && rows.length === 0" class="result-empty">
          <span class="empty-palette"><i></i><i></i><i></i></span>
          <h3>没有找到相近图片</h3>
          <p>当前空间图片可能还没有主色信息，可以换一种颜色继续搜索。</p>
        </div>
        <div v-else-if="!searching && !searched" class="result-empty">
          <span class="empty-palette"><i></i><i></i><i></i></span>
          <h3>等待你的第一种颜色</h3>
          <p>从上方推荐色板或取色器中选择颜色，开始发现相近素材。</p>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.color-page { position: relative; isolation: isolate; min-height: calc(100vh - 72px); overflow: hidden; padding-bottom: 70px; }
.color-page::before { content: ''; position: absolute; z-index: -2; inset: 0 0 auto; height: 610px; background: radial-gradient(circle at 7% 8%, color-mix(in srgb, var(--active-color) 22%, #bfeaff), transparent 31%), radial-gradient(circle at 92% 3%, color-mix(in srgb, var(--active-color) 24%, #ffdce7), transparent 28%); transition: background .45s ease; }
.color-orb { position: absolute; z-index: -1; border-radius: 50%; pointer-events: none; animation: color-drift 8s ease-in-out infinite alternate; }
.color-orb--one { width: 210px; height: 210px; left: -110px; top: 680px; background: color-mix(in srgb, var(--active-color) 18%, transparent); }
.color-orb--two { width: 280px; height: 280px; right: -150px; top: 980px; background: rgba(159,220,244,.17); animation-delay: -3s; }

.color-hero { position: relative; z-index: 1; min-height: 320px; display: flex; align-items: center; justify-content: space-between; gap: 30px; margin-bottom: 18px; padding: 48px clamp(28px,5vw,68px); overflow: hidden; border: 1px solid rgba(255,255,255,.84); border-radius: 32px; background: linear-gradient(125deg, rgba(255,255,255,.9), color-mix(in srgb, var(--active-color) 12%, rgba(255,255,255,.92))); box-shadow: 0 26px 68px rgba(41,46,58,.1); transition: background .45s ease; }
.color-hero::after { content: ''; position: absolute; width: 430px; height: 430px; right: -180px; top: -230px; border-radius: 50%; border: 70px solid rgba(255,255,255,.24); }
.color-hero__copy { position: relative; z-index: 1; max-width: 700px; }
.color-eyebrow { display: flex; align-items: center; gap: 9px; margin-bottom: 13px; color: #9b6979; font-size: 11px; font-weight: 900; letter-spacing: 2px; }
.color-eyebrow span { width: 24px; height: 2px; border-radius: 2px; background: linear-gradient(90deg,#70cae9,var(--active-color)); }
.color-hero h1 { margin: 0; color: #1c2027; font-size: clamp(38px,5vw,64px); line-height: 1.05; font-weight: 950; letter-spacing: -3px; }
.color-hero p { max-width: 600px; margin: 15px 0 0; color: #7d8794; font-size: 15px; line-height: 1.75; }
.color-hero__actions { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 24px; }
.color-hero__actions .el-button { height: 40px; background: rgba(255,255,255,.7); backdrop-filter: blur(10px); }
.color-hero__visual { position: relative; z-index: 1; width: 240px; height: 240px; display: grid; place-items: center; flex-shrink: 0; }
.color-ring { position: absolute; border-radius: 50%; border: 1px solid color-mix(in srgb, var(--active-color) 28%, white); animation: ring-breathe 3.4s ease-in-out infinite; }
.color-ring--outer { inset: 0; background: color-mix(in srgb, var(--active-color) 8%, rgba(255,255,255,.4)); box-shadow: inset 0 0 50px rgba(255,255,255,.5); }
.color-ring--middle { inset: 28px; animation-delay: -.8s; }
.color-core { position: relative; width: 132px; height: 132px; display: grid; place-items: center; border: 12px solid rgba(255,255,255,.72); border-radius: 50%; background: var(--active-color); box-shadow: 0 24px 48px color-mix(in srgb, var(--active-color) 36%, transparent), inset -18px -22px 32px rgba(38,42,52,.12), inset 15px 15px 28px rgba(255,255,255,.3); transition: background .35s ease, box-shadow .35s ease; }
.color-core i { width: 26px; height: 26px; border-radius: 50%; background: rgba(255,255,255,.72); filter: blur(2px); transform: translate(-22px,-24px); }
.color-hero__visual b { position: absolute; bottom: -3px; padding: 7px 12px; border-radius: 999px; color: #515a66; background: rgba(255,255,255,.82); box-shadow: 0 10px 25px rgba(43,48,58,.1); font-size: 11px; letter-spacing: 1px; }

.color-skeleton { position: relative; z-index: 1; }
.color-state { position: relative; z-index: 1; min-height: 430px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 24px; border: 1px solid rgba(225,228,236,.9); border-radius: 28px; background: rgba(255,255,255,.84); box-shadow: 0 20px 55px rgba(39,45,58,.07); text-align: center; backdrop-filter: blur(16px); }
.state-icon { width: 74px; height: 74px; display: grid; place-items: center; border-radius: 26px 9px 26px 9px; color: #fff; background: linear-gradient(145deg,#70cae9,var(--active-color)); box-shadow: 14px 14px 0 color-mix(in srgb,var(--active-color) 14%,transparent); font-size: 30px; }
.state-icon--error { background: linear-gradient(145deg,#f2a278,#e7687b); }
.color-state h2 { margin: 28px 0 0; color: #292e37; font-size: 25px; font-weight: 900; }
.color-state p { max-width: 540px; margin: 12px auto 24px; color: #8f98a4; font-size: 14px; line-height: 1.8; }

.color-workbench { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(250px,.72fr) minmax(0,1.28fr); margin-bottom: 18px; overflow: hidden; border: 1px solid rgba(224,228,236,.92); border-radius: 27px; background: rgba(255,255,255,.91); box-shadow: 0 18px 48px rgba(39,45,58,.08); backdrop-filter: blur(16px); }
.color-preview { position: relative; min-height: 330px; display: grid; place-items: center; overflow: hidden; background: linear-gradient(145deg, color-mix(in srgb,var(--active-color) 20%,#f8fbfd), color-mix(in srgb,var(--active-color) 8%,white)); transition: background .4s ease; }
.preview-glow { position: absolute; width: 260px; height: 260px; border-radius: 50%; background: var(--active-color); opacity: .18; filter: blur(40px); animation: preview-float 4s ease-in-out infinite; }
.preview-swatch { position: relative; width: 178px; height: 210px; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 12px solid rgba(255,255,255,.84); border-radius: 90px 90px 24px 24px; background: var(--active-color); box-shadow: 0 28px 54px color-mix(in srgb,var(--active-color) 34%,transparent), inset -20px -26px 36px rgba(35,40,50,.12), inset 18px 20px 30px rgba(255,255,255,.25); transform: rotate(-4deg); transition: background .35s ease, box-shadow .35s ease; }
.preview-swatch span { position: absolute; width: 38px; height: 38px; left: 34px; top: 30px; border-radius: 50%; background: rgba(255,255,255,.55); filter: blur(2px); }
.preview-swatch strong { margin-top: 110px; padding: 7px 11px; border-radius: 999px; color: #4b535e; background: rgba(255,255,255,.82); font-size: 10px; letter-spacing: 1px; }
.space-chip { position: absolute; left: 20px; bottom: 20px; display: inline-flex; align-items: center; gap: 6px; max-width: calc(100% - 40px); padding: 7px 11px; overflow: hidden; border-radius: 999px; color: #65707c; background: rgba(255,255,255,.76); font-size: 11px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; backdrop-filter: blur(10px); }
.color-controls { padding: clamp(26px,4vw,46px); }
.workbench-heading > div { display: flex; align-items: center; gap: 10px; }
.workbench-heading span { color: var(--active-color); font-size: 11px; font-weight: 900; }
.workbench-heading h2 { margin: 0; color: #292e37; font-size: 22px; font-weight: 900; }
.workbench-heading p { margin: 10px 0 0; color: #929ba7; font-size: 12px; line-height: 1.7; }
.preset-list { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 9px; margin-top: 25px; }
.preset-list button { display: flex; align-items: center; gap: 9px; min-width: 0; padding: 10px 12px; border: 1px solid #edf0f4; border-radius: 13px; color: #747e8a; background: #fbfcfe; cursor: pointer; transition: transform .22s ease,border-color .22s ease,background .22s ease; }
.preset-list button:hover { transform: translateY(-3px); border-color: color-mix(in srgb,var(--active-color) 35%,#e9ebf0); background: #fff; }
.preset-list button.active { border-color: color-mix(in srgb,var(--active-color) 50%,#e9ebf0); background: color-mix(in srgb,var(--active-color) 7%,white); box-shadow: 0 8px 20px color-mix(in srgb,var(--active-color) 12%,transparent); }
.preset-list i { width: 24px; height: 24px; flex-shrink: 0; border: 4px solid #fff; border-radius: 50%; box-shadow: 0 0 0 1px #e5e8ed; }
.preset-list span { overflow: hidden; font-size: 11px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.color-input-row { display: grid; grid-template-columns: 42px minmax(140px,1fr) auto; gap: 10px; align-items: center; margin-top: 22px; }
.color-input-row :deep(.el-color-picker__trigger) { width: 42px; height: 42px; border-radius: 13px; }
.color-input-row :deep(.el-input__wrapper) { min-height: 42px; }
.color-input-row .el-button { height: 42px; }
.hex-mark { color: #a0a8b3; font-size: 10px; font-weight: 900; letter-spacing: 1px; }
.search-note { display: flex; align-items: center; gap: 6px; margin-top: 13px; color: #9ca4ae; font-size: 11px; }

.color-results { position: relative; z-index: 1; padding: 25px; border: 1px solid rgba(224,228,236,.92); border-radius: 27px; background: rgba(255,255,255,.87); box-shadow: 0 18px 48px rgba(39,45,58,.065); backdrop-filter: blur(16px); }
.results-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; margin-bottom: 22px; }
.results-kicker { margin-bottom: 7px; color: var(--active-color); font-size: 10px; font-weight: 900; letter-spacing: 1.5px; }
.results-head h2 { margin: 0; color: #292e37; font-size: 22px; font-weight: 900; }
.results-head p { margin: 7px 0 0; color: #9aa3ae; font-size: 12px; }
.result-count { display: inline-flex; align-items: center; gap: 8px; flex-shrink: 0; padding: 7px 11px; border-radius: 999px; color: #606a76; background: #f5f7fa; font-size: 11px; font-weight: 800; }
.result-count i { width: 8px; height: 8px; border-radius: 50%; background: var(--active-color); box-shadow: 0 0 0 5px color-mix(in srgb,var(--active-color) 13%,transparent); }
.results-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(240px,1fr)); gap: 18px; min-height: 100px; }
.color-item { position: relative; min-width: 0; }
.distance { position: absolute; z-index: 3; top: 10px; right: 10px; display: inline-flex; align-items: center; gap: 6px; padding: 6px 9px; border: 1px solid rgba(255,255,255,.72); border-radius: 999px; color: #fff; background: rgba(30,34,41,.68); font-size: 10px; font-weight: 800; backdrop-filter: blur(10px); }
.distance i { width: 8px; height: 8px; border-radius: 50%; background: var(--active-color); box-shadow: 0 0 0 3px rgba(255,255,255,.16); }
.result-empty { min-height: 250px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 28px; text-align: center; }
.empty-palette { display: flex; align-items: center; }
.empty-palette i { width: 42px; height: 42px; border: 5px solid #fff; border-radius: 50%; background: var(--active-color); box-shadow: 0 7px 18px color-mix(in srgb,var(--active-color) 22%,transparent); }
.empty-palette i:nth-child(2) { margin-left: -10px; opacity: .62; transform: translateY(7px); }
.empty-palette i:nth-child(3) { margin-left: -10px; opacity: .34; }
.result-empty h3 { margin: 22px 0 0; color: #3a404a; font-size: 17px; font-weight: 900; }
.result-empty p { max-width: 460px; margin: 8px 0 0; color: #9ba3ae; font-size: 12px; line-height: 1.7; }

@keyframes color-drift { to { transform: translate(32px,-25px) scale(1.1); } }
@keyframes ring-breathe { 0%,100% { transform: scale(.94); opacity: .58; } 50% { transform: scale(1.05); opacity: 1; } }
@keyframes preview-float { 50% { transform: translateY(-14px) scale(1.08); } }
@media (max-width: 900px) {
  .color-workbench { grid-template-columns: 1fr; }
  .color-preview { min-height: 280px; }
}
@media (max-width: 720px) {
  .color-page { min-height: calc(100vh - 62px); padding-left: 16px; padding-right: 16px; }
  .color-hero { align-items: flex-start; flex-direction: column; padding: 32px 24px; }
  .color-hero h1 { letter-spacing: -2px; }
  .color-hero__visual { align-self: center; width: 210px; height: 210px; }
  .preset-list { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .color-input-row { grid-template-columns: 42px 1fr; }
  .color-input-row .el-button { grid-column: 1 / -1; }
  .results-head { align-items: flex-start; flex-direction: column; }
  .color-results { padding: 20px 15px; }
}
@media (max-width: 480px) { .results-grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) {
  .color-orb,.color-ring,.preview-glow { animation: none; }
  .preset-list button { transition: none; }
  .preset-list button:hover { transform: none; }
}
</style>
