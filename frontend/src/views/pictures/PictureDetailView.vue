<script setup lang="ts">
/**
 * 图片详情：大图预览 + 素材信息 + 下载/相似图/分享
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { pictureApi } from '@/api/picture'
import type { PictureRead } from '@/types/picture'
import SimilarSearchDialog from '@/components/SimilarSearchDialog.vue'
import ShareDialog from '@/components/ShareDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useAuthGateStore } from '@/stores/authGate'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const authGate = useAuthGateStore()

const loading = ref(false)
const notFound = ref(false)
const loadError = ref('')
const detail = ref<PictureRead | null>(null)
const similarVisible = ref(false)
const shareVisible = ref(false)

const id = computed(() => Number(route.params.id))

type DetailTextRow = { label: string; type: 'text'; value: string }
type DetailChipRow = { label: string; type: 'chips'; chips: string[] }
type DetailRow = DetailTextRow | DetailChipRow
type DetailStat = { label: string; value: string; icon: string; tone: 'rose' | 'sky' | 'mint' | 'lavender' }

function formatSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '未知'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDateTime(value: string | null): string {
  if (!value) return '未填写'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    hour12: false,
  }).format(date)
}

function formatDimension(picWidth: number | null, picHeight: number | null): string {
  if (!picWidth || !picHeight) return '未填写'
  return `${picWidth} × ${picHeight}`
}

function startDownload(): void {
  const url = pictureApi.downloadUrl(id.value)
  const downloadWindow = window.open(url, '_blank')
  if (downloadWindow) {
    downloadWindow.opener = null
  } else {
    authGate.showDownloadFallback(url)
  }
}

async function handleDownload(): Promise<void> {
  if (!auth.isAuthenticated) {
    const authenticated = await authGate.requireAuthentication({ reason: '登录后即可下载原图' })
    if (!authenticated) return
  }
  startDownload()
}

async function handleSimilarSearch(): Promise<void> {
  const authenticated = await authGate.requireAuthentication({ reason: '登录后即可搜索相似图片' })
  if (authenticated) similarVisible.value = true
}

const detailFigureStyle = computed(() => {
  const width = detail.value?.pic_width
  const height = detail.value?.pic_height
  const aspectRatio = width && height ? width / height : 16 / 10

  return {
    aspectRatio: String(aspectRatio),
    maxWidth: `${Math.round(620 * aspectRatio)}px`,
  }
})

const detailStats = computed<DetailStat[]>(() => {
  if (!detail.value) return []
  return [
    { label: '尺寸', value: formatDimension(detail.value.pic_width, detail.value.pic_height), icon: 'FullScreen', tone: 'sky' },
    { label: '格式', value: detail.value.pic_format || '未填写', icon: 'Document', tone: 'lavender' },
    { label: '大小', value: formatSize(detail.value.pic_size), icon: 'Coin', tone: 'mint' },
    { label: '下载次数', value: String(detail.value.download_count), icon: 'Download', tone: 'rose' },
  ]
})

const detailRows = computed<DetailRow[]>(() => {
  if (!detail.value) return []
  return [
    { label: '分类', type: 'text', value: detail.value.category || '未填写' },
    { label: '标签', type: 'chips', chips: detail.value.tags },
    { label: '简介', type: 'text', value: detail.value.introduction || '未填写' },
    { label: '尺寸', type: 'text', value: formatDimension(detail.value.pic_width, detail.value.pic_height) },
    { label: '格式', type: 'text', value: detail.value.pic_format || '未填写' },
    { label: '大小', type: 'text', value: formatSize(detail.value.pic_size) },
    { label: '色彩模式', type: 'text', value: detail.value.color_mode || '未填写' },
    { label: '下载次数', type: 'text', value: String(detail.value.download_count) },
    { label: '上传者 ID', type: 'text', value: String(detail.value.user_id) },
    { label: '创建时间', type: 'text', value: formatDateTime(detail.value.created_at) },
  ]
})

onMounted(async () => {
  loading.value = true
  try {
    detail.value = await pictureApi.get(id.value)
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 401) {
      loadError.value = '公共图片详情接口尚未开放游客访问，请联系后端开放只读详情接口。'
    } else if (status === 404) {
      notFound.value = true
    } else {
      loadError.value = '图片详情加载失败，请稍后重试'
      ElMessage.error(loadError.value)
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="picture-detail-page page-container">
    <section class="detail-hero analytics-reveal">
      <span class="detail-hero__orb detail-hero__orb--sky" aria-hidden="true"></span>
      <span class="detail-hero__orb detail-hero__orb--rose" aria-hidden="true"></span>
      <div class="detail-hero__pixels" aria-hidden="true"><i v-for="index in 8" :key="index"></i></div>

      <div class="detail-hero__copy">
        <el-button class="detail-back-button" :icon="'ArrowLeft'" round @click="router.push('/pictures')">返回探索</el-button>
        <div class="eyebrow">DETAIL PAGE · 素材档案</div>
        <h1>{{ detail?.name || '图片详情' }}</h1>
        <p>查看高清预览、素材规格与完整标签，也可以下载、分享或继续搜索相似灵感。</p>
      </div>

      <div class="detail-nav-pills">
        <router-link to="/pictures" class="detail-nav-pill">公共图库</router-link>
        <span class="detail-nav-pill is-active">详情页</span>
        <router-link to="/spaces" class="detail-nav-pill">个人空间</router-link>
        <router-link to="/spaces/team" class="detail-nav-pill">团队空间</router-link>
      </div>
    </section>

    <el-skeleton v-if="loading" :rows="8" animated />

    <el-result
      v-else-if="loadError"
      icon="warning"
      title="暂时无法浏览图片详情"
      :sub-title="loadError"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/pictures')">返回图片库</el-button>
      </template>
    </el-result>

    <el-result
      v-else-if="notFound || !detail"
      icon="warning"
      title="图片不存在或未发布"
      sub-title="该图片可能已被删除或尚未通过审核"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/pictures')">返回图片库</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="detail-grid">
        <div class="detail-stack">
          <el-card class="detail-card detail-figure-card" shadow="never">
            <div class="detail-figure" :style="detailFigureStyle">
              <el-image
                class="detail-image"
                :src="detail.url"
                fit="contain"
                :preview-src-list="[detail.url]"
                preview-teleported
              />
            </div>

            <div class="detail-section">
              <div class="detail-section-head">
                <div>
                  <h3 class="detail-title">{{ detail.name }}</h3>
                  <p class="detail-desc">{{ detail.introduction || '暂无简介，当前素材信息以右侧详情为准。' }}</p>
                </div>

                <el-tag effect="plain" round type="info">图片 ID {{ detail.id }}</el-tag>
              </div>

              <div class="detail-meta-grid">
                <div v-for="stat in detailStats" :key="stat.label" class="detail-stat" :class="`detail-stat--${stat.tone}`">
                  <span class="detail-stat__icon"><el-icon><component :is="stat.icon" /></el-icon></span>
                  <span class="detail-stat__copy"><small>{{ stat.label }}</small><strong>{{ stat.value }}</strong></span>
                </div>
              </div>
            </div>
          </el-card>
        </div>

        <div class="detail-side">
          <el-card class="detail-card detail-side-card" shadow="never">
            <template #header>
              <div class="detail-side-head">
                <span class="detail-side-icon"><el-icon><Tickets /></el-icon></span>
                <div class="detail-side-head__copy">
                  <h3 class="detail-side-title">素材信息</h3>
                  <div class="detail-side-note">第 {{ detail.id }} 号</div>
                </div>
              </div>
            </template>

            <div class="detail-table">
              <div v-for="row in detailRows" :key="row.label" class="detail-row">
                <div class="detail-label">{{ row.label }}</div>
                <div class="detail-value">
                  <template v-if="row.type === 'chips'">
                    <div v-if="row.chips.length" class="detail-pill-list">
                      <span v-for="chip in row.chips" :key="chip" class="detail-pill">{{ chip }}</span>
                    </div>
                    <span v-else class="detail-muted">未填写</span>
                  </template>
                  <template v-else>
                    {{ row.value }}
                  </template>
                </div>
              </div>
            </div>
          </el-card>

          <el-card class="detail-card detail-side-card detail-action-card" shadow="never">
            <template #header>
              <div class="detail-side-head">
                <span class="detail-side-icon detail-side-icon--action"><el-icon><MagicStick /></el-icon></span>
                <div class="detail-side-head__copy">
                  <h3 class="detail-side-title">操作</h3>
                  <div class="detail-side-note">下载、分享、搜索相似图</div>
                </div>
              </div>
            </template>

            <div class="detail-action-list">
              <el-button type="primary" @click="handleDownload">
                <el-icon><Download /></el-icon>
                下载原图
              </el-button>
              <el-button @click="shareVisible = true">
                <el-icon><Share /></el-icon>
                分享素材
              </el-button>
              <el-button @click="handleSimilarSearch">
                <el-icon><Search /></el-icon>
                搜相似图
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </template>

    <SimilarSearchDialog v-model="similarVisible" :picture-id="detail?.id ?? 0" kind="picture" />
    <ShareDialog v-model="shareVisible" :url="detail?.url ?? ''" />
  </div>
</template>

<style scoped>
.picture-detail-page {
  position: relative;
  isolation: isolate;
  min-height: calc(100vh - 72px);
  overflow: hidden;
}

.picture-detail-page::before,
.picture-detail-page::after {
  content: '';
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  filter: blur(2px);
  pointer-events: none;
}

.picture-detail-page::before {
  width: 330px;
  height: 330px;
  left: -150px;
  top: 520px;
  background: rgba(159,220,244,.14);
}

.picture-detail-page::after {
  width: 280px;
  height: 280px;
  right: -130px;
  top: 810px;
  background: rgba(236,114,150,.11);
}

.detail-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 28px;
  min-height: 268px;
  margin-bottom: 20px;
  padding: clamp(30px, 4.6vw, 54px);
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.9);
  border-radius: 30px;
  background:
    linear-gradient(120deg, rgba(235,249,253,.97), rgba(255,246,249,.96) 57%, rgba(241,237,255,.94));
  box-shadow: 0 24px 70px rgba(62,69,87,.1);
}

.detail-hero::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: .22;
  background-image: linear-gradient(rgba(255,255,255,.88) 1px, transparent 1px), linear-gradient(90deg,rgba(255,255,255,.88) 1px,transparent 1px);
  background-size: 36px 36px;
  mask-image: linear-gradient(100deg, #000, transparent 82%);
}

.detail-hero__copy { position: relative; z-index: 2; min-width: 0; }
.detail-back-button { height: 35px; margin-bottom: 25px; padding: 0 15px !important; color: #835e6b !important; border-color: rgba(221,183,195,.82) !important; background: rgba(255,255,255,.64) !important; box-shadow: 0 8px 20px rgba(69,74,88,.065); backdrop-filter: blur(10px); transition: transform .22s ease, box-shadow .22s ease, color .22s ease !important; }
.detail-back-button:hover, .detail-back-button:focus-visible { color: #bc5676 !important; border-color: #eca6bb !important; background: #fff !important; transform: translateX(-3px); box-shadow: 0 11px 24px rgba(190,86,119,.13); }
.detail-back-button:focus-visible { outline: 3px solid rgba(236,114,150,.14); outline-offset: 2px; }
.detail-hero .eyebrow { position: relative; z-index: 2; margin-bottom: 10px; }
.detail-hero h1 { position: relative; z-index: 2; max-width: 820px; margin: 0; overflow-wrap: anywhere; color: #191d24; font-size: clamp(34px, 4.2vw, 58px); line-height: 1.08; letter-spacing: -2px; font-weight: 900; }
.detail-hero h1::after { content: ''; display: inline-block; width: 11px; height: 11px; margin-left: 10px; border-radius: 4px; background: linear-gradient(135deg,#82cce8,#ec7296); box-shadow: 7px -7px 0 rgba(155,137,223,.26); transform: rotate(8deg); }
.detail-hero p { position: relative; z-index: 2; max-width: 660px; margin: 16px 0 0; color: #78818d; font-size: 14px; line-height: 1.85; }
.detail-hero .detail-nav-pills { position: relative; z-index: 2; justify-content: flex-end; max-width: 430px; padding: 0; }
.detail-hero .detail-nav-pill { min-height: 36px; border-color: rgba(220,223,232,.84); background: rgba(255,255,255,.61); backdrop-filter: blur(10px); transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.detail-hero .detail-nav-pill:hover { transform: translateY(-2px); box-shadow: 0 9px 20px rgba(65,72,91,.08); }
.detail-hero .detail-nav-pill.is-active { border-color: transparent; background: linear-gradient(105deg,#e86f93,#aa85d4); box-shadow: 0 11px 25px rgba(210,100,139,.25); }

.detail-hero__orb { position: absolute; z-index: 1; border-radius: 50%; animation: detail-orb 8s ease-in-out infinite; }
.detail-hero__orb--sky { width: 210px; height: 210px; top: -105px; right: 31%; background: rgba(114,201,234,.25); }
.detail-hero__orb--rose { width: 170px; height: 170px; right: -47px; bottom: -74px; background: rgba(236,114,150,.2); animation-delay: -3s; }
.detail-hero__pixels { position: absolute; z-index: 1; inset: 0; pointer-events: none; }
.detail-hero__pixels i { position: absolute; width: 10px; height: 10px; border-radius: 3px; background: rgba(236,114,150,.42); animation: detail-pixel 5s ease-in-out infinite; }
.detail-hero__pixels i:nth-child(1) { left: 5%; top: 24%; }.detail-hero__pixels i:nth-child(2) { left: 44%; top: 13%; background: rgba(104,205,181,.5); animation-delay: -1s; }.detail-hero__pixels i:nth-child(3) { right: 7%; top: 18%; background: rgba(98,196,233,.5); animation-delay: -2s; }.detail-hero__pixels i:nth-child(4) { right: 25%; bottom: 13%; width: 7px; height: 7px; background: rgba(155,137,223,.48); }.detail-hero__pixels i:nth-child(n+5) { display: none; }

.detail-grid { grid-template-columns: minmax(0, 1.4fr) minmax(330px, .6fr); gap: 20px; }
.detail-card { border: 1px solid rgba(226,229,237,.88) !important; background: rgba(255,255,255,.88) !important; box-shadow: 0 17px 48px rgba(43,48,62,.075) !important; backdrop-filter: blur(16px); }
.detail-figure-card { animation: detail-reveal .72s 80ms cubic-bezier(.22,1,.36,1) both; }
.detail-figure-card :deep(.el-card__body) { padding: 22px 22px 25px; }
.detail-figure { position: relative; width: 100%; height: auto; min-height: 0; margin-inline: auto; padding: 0; isolation: isolate; overflow: hidden; background: transparent; box-shadow: none; }
.detail-image { position: absolute; z-index: 1; inset: 0; width: 100%; height: 100%; max-height: none; filter: none; }
.detail-image :deep(.el-image__inner) { width: 100%; height: 100%; object-fit: contain !important; object-position: center; }
.detail-image :deep(.el-image__wrapper) { width: 100%; height: 100%; }

.detail-section { padding: 24px 4px 3px; }
.detail-title { font-size: clamp(24px,2.3vw,32px); letter-spacing: -.6px; }
.detail-desc { max-width: 820px; }
.detail-section-head :deep(.el-tag) { flex: 0 0 auto; background: #f5f1ff; border-color: #ded5fb; color: #7565aa; }
.detail-meta-grid { grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px; margin-top: 22px; }
.detail-stat { --stat-tone: #ec7296; --stat-soft: #fff0f5; display: flex; align-items: center; gap: 11px; min-width: 0; padding: 13px; border: 1px solid color-mix(in srgb,var(--stat-tone) 12%,#eceef3); border-radius: 16px; background: linear-gradient(145deg,#fff,var(--stat-soft)); transition: transform .25s ease, box-shadow .25s ease; }
.detail-stat:hover { transform: translateY(-4px); box-shadow: 0 12px 25px color-mix(in srgb,var(--stat-tone) 13%,transparent); }
.detail-stat--sky { --stat-tone: #55b7dd; --stat-soft: #eaf9ff; }.detail-stat--mint { --stat-tone: #54bba3; --stat-soft: #e9faf6; }.detail-stat--lavender { --stat-tone: #8a79cb; --stat-soft: #f1edff; }
.detail-stat__icon { display: grid !important; place-items: center; flex: 0 0 auto; width: 34px; height: 34px; border-radius: 11px; color: var(--stat-tone) !important; background: color-mix(in srgb,var(--stat-soft) 75%,#fff); }
.detail-stat__copy { min-width: 0; }.detail-stat__copy small { display: block; color: #999fa9; font-size: 10px; font-weight: 700; }.detail-stat__copy strong { display: block; overflow: hidden; margin-top: 4px; color: #30343c; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }

.detail-side { position: sticky; top: 86px; animation: detail-reveal .72s 160ms cubic-bezier(.22,1,.36,1) both; }
.detail-side-card :deep(.el-card__header) { padding: 20px 22px 0; border-bottom: 0; }
.detail-side-card :deep(.el-card__body) { padding: 18px 22px 22px; }
.detail-side-head { align-items: center; justify-content: flex-start; margin: 0; }
.detail-side-icon { display: grid; place-items: center; flex: 0 0 auto; width: 42px; height: 42px; border-radius: 14px; color: #c45a7a; background: #fff0f5; }
.detail-side-icon--action { color: #fff; background: rgba(255,255,255,.15); }
.detail-side-head__copy { min-width: 0; }
.detail-side-title { font-size: 17px; }
.detail-side-note { margin-top: 4px; color: #9da4ae; font-size: 10px; }
.detail-table { border-color: #eceef3; border-radius: 16px; background: rgba(255,255,255,.72); }
.detail-row { grid-template-columns: 94px minmax(0,1fr); border-color: #f0f1f4; transition: background .18s ease; }
.detail-row:hover { background: #fff9fb; }
.detail-label { padding: 12px 13px; background: rgba(248,249,252,.8); color: #939ba7; font-size: 11px; }
.detail-value { padding: 12px 13px; overflow-wrap: anywhere; color: #444a54; font-size: 12px; }
.detail-pill { min-height: 25px; padding: 0 9px; font-size: 10px; }

.detail-action-card { position: relative; overflow: hidden; border-color: transparent !important; background: linear-gradient(145deg,#657593,#8c7595 58%,#bd718d) !important; box-shadow: 0 19px 43px rgba(91,76,105,.2) !important; }
.detail-action-card::before { content: ''; position: absolute; width: 160px; height: 160px; right: -70px; top: -90px; border-radius: 50%; background: rgba(255,255,255,.1); }
.detail-action-card .detail-side-title { color: #fff; }.detail-action-card .detail-side-note { color: rgba(255,255,255,.64); }
.detail-action-card :deep(.el-card__header), .detail-action-card :deep(.el-card__body) { position: relative; z-index: 1; }
.detail-action-list { gap: 9px; }
.detail-action-list :deep(.el-button) { height: 44px; margin-left: 0; border-color: rgba(255,255,255,.2); color: #fff; background: rgba(255,255,255,.1); box-shadow: none; backdrop-filter: blur(8px); transition: transform .22s ease, background .22s ease, box-shadow .22s ease; }
.detail-action-list :deep(.el-button:hover) { border-color: rgba(255,255,255,.36); color: #fff; background: rgba(255,255,255,.18); transform: translateY(-2px); box-shadow: 0 9px 20px rgba(50,42,62,.13); }
.detail-action-list :deep(.el-button--primary) { border-color: #fff; color: #9b5974; background: #fff; box-shadow: 0 10px 23px rgba(47,40,58,.16); }
.detail-action-list :deep(.el-button--primary:hover) { color: #b94f72; background: #fff; }

.picture-detail-page :deep(.el-result) { border: 1px solid rgba(226,229,237,.86); border-radius: 24px; background: rgba(255,255,255,.78); box-shadow: 0 16px 42px rgba(43,48,61,.07); }

@keyframes detail-orb { 0%,100% { transform: translate(0,0); } 50% { transform: translate(14px,-10px); } }
@keyframes detail-pixel { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-8px) rotate(10deg); } }
@keyframes detail-reveal { from { transform: translateY(18px); opacity: 0; } }

@media (max-width: 1100px) {
  .detail-hero { grid-template-columns: 1fr; align-items: start; }.detail-hero .detail-nav-pills { justify-content: flex-start; max-width: none; }
  .detail-grid { grid-template-columns: 1fr; }.detail-side { position: static; grid-template-columns: minmax(0,1.2fr) minmax(280px,.8fr); align-items: start; }
  .detail-meta-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
}

@media (max-width: 720px) {
  .detail-hero { min-height: auto; padding: 27px 22px; border-radius: 24px; }.detail-hero h1 { font-size: 36px; letter-spacing: -1.3px; }.detail-hero .detail-nav-pills { gap: 7px; }.detail-hero .detail-nav-pill { min-height: 32px; padding: 0 11px; font-size: 11px; }
  .detail-side { grid-template-columns: 1fr; }.detail-figure-card :deep(.el-card__body) { padding: 12px 12px 18px; }.detail-figure { height: auto; min-height: 0; padding: 0; border-radius: 17px; }.detail-section { padding: 20px 4px 3px; }.detail-section-head { flex-direction: column; }.detail-meta-grid { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 440px) {
  .detail-hero h1 { font-size: 31px; }.detail-hero p { font-size: 12px; }.detail-figure { height: auto; min-height: 0; padding: 0; }.detail-meta-grid { grid-template-columns: 1fr; }.detail-stat { padding: 12px; }
  .detail-row { grid-template-columns: 1fr; }.detail-label { padding-bottom: 4px; background: transparent; }.detail-value { padding-top: 2px; }
}

@media (prefers-reduced-motion: reduce) {
  .detail-hero__orb, .detail-hero__pixels i, .detail-figure-card, .detail-side { animation: none; }
  .detail-back-button, .detail-nav-pill, .detail-stat, .detail-action-list :deep(.el-button) { transition: none; }
  .detail-back-button:hover, .detail-nav-pill:hover, .detail-stat:hover, .detail-action-list :deep(.el-button:hover) { transform: none; }
}
</style>
