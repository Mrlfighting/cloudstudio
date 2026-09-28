<script setup lang="ts">
/**
 * 用户端图片列表：搜索 / 分类 / 排序 / 分页（登录用户可上传）
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { pictureApi } from '@/api/picture'
import { getErrorMessage } from '@/api/http'
import { useAuthGateStore } from '@/stores/authGate'
import { PICTURE_CATEGORIES, type PictureListItemRead, type PictureSort } from '@/types/picture'
import PictureCard from '@/components/PictureCard.vue'
import PictureUploadDialog from '@/components/PictureUploadDialog.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const authGate = useAuthGateStore()

const loading = ref(false)
const rows = ref<PictureListItemRead[]>([])
const uploadVisible = ref(false)
const loadError = ref('')

const filters = reactive({
  keyword: '',
  category: '',
  sort: 'time' as PictureSort,
})

const pagination = reactive({
  page: 1,
  itemsPerPage: 20,
  total: 0,
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await pictureApi.list({
      page: pagination.page,
      items_per_page: pagination.itemsPerPage,
      category: filters.category || undefined,
      keyword: filters.keyword || undefined,
      sort: filters.sort,
    })
    rows.value = res.data
    pagination.total = res.total_count
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 401) {
      rows.value = []
      pagination.total = 0
      loadError.value = '公共图库接口尚未开放游客访问，请联系后端开放只读列表接口。'
    } else {
      loadError.value = getErrorMessage(err, '获取图片列表失败')
      ElMessage.error(loadError.value)
    }
  } finally {
    loading.value = false
  }
}

async function openUpload(): Promise<void> {
  const authenticated = await authGate.requireAuthentication({ reason: '登录后即可上传图片' })
  if (authenticated) uploadVisible.value = true
}

function resetAndLoad() {
  pagination.page = 1
  load()
}

function onPageChange() {
  load()
}

function onSizeChange() {
  pagination.page = 1
  load()
}

onMounted(load)
</script>

<template>
  <div class="explore-page">
    <section class="explore-hero">
      <div class="hero-orbit orbit-one" aria-hidden="true"></div>
      <div class="hero-orbit orbit-two" aria-hidden="true"></div>
      <div class="hero-pixel-field" aria-hidden="true"><i v-for="index in 12" :key="index"></i></div>
      <div class="hero-visual-note hero-visual-note--left" aria-hidden="true">
        <span><el-icon><PictureFilled /></el-icon></span>
        <div><strong>每日灵感</strong><small>持续发现好作品</small></div>
      </div>
      <div class="hero-visual-note hero-visual-note--right" aria-hidden="true">
        <span class="note-dots"><i></i><i></i><i></i></span>
        <div><strong>精选图库</strong><small>多种分类自由探索</small></div>
      </div>
      <div class="hero-copy">
        <span class="eyebrow"><el-icon><MagicStick /></el-icon>灵感正在发生</span>
        <h1>把灵感<br /><em>收藏成作品</em></h1>
        <p>从一张图片开始，发现设计、收集灵感，和团队一起做出更好的作品。</p>
      </div>
      <div class="hero-search">
        <el-icon><Search /></el-icon>
        <el-input
          v-model="filters.keyword"
          class="hero-input"
          placeholder="搜索背景、海报、插画、字体..."
          clearable
          @keyup.enter="resetAndLoad"
          @clear="resetAndLoad"
        />
        <span class="search-shortcut">Enter</span>
        <el-button class="search-submit" circle @click="resetAndLoad"><el-icon><ArrowUpRight /></el-icon></el-button>
      </div>
      <div class="hero-meta">
        <span>为你找到 <strong>{{ pagination.total.toLocaleString() }}</strong> 张灵感</span>
        <span class="meta-separator"></span>
        <span>实时同步社区图片</span>
        <button class="text-link" @click="router.push('/pictures/my')"><el-icon><Upload /></el-icon>我的上传</button>
      </div>
    </section>

    <section class="workspace">
      <aside class="sidebar">
        <div class="sidebar-heading">
          <div>
            <span class="section-kicker">DISCOVER</span>
            <h2>发现好素材</h2>
          </div>
        </div>
        <div class="side-menu">
          <button class="side-menu-item" :class="{ active: !filters.category }" @click="filters.category = ''; resetAndLoad()">
            <el-icon><Layers /></el-icon>全部素材
          </button>
          <button class="side-menu-item" :class="{ active: filters.sort === 'popularity' }" @click="filters.sort = 'popularity'; resetAndLoad()">
            <el-icon><TrendCharts /></el-icon>热门趋势
          </button>
        </div>
        <div class="side-divider"></div>
        <div class="sidebar-heading compact"><span>主题分类</span><button class="text-button" @click="filters.category = ''; resetAndLoad()">全部</button></div>
        <div class="category-list">
          <button v-for="(c, index) in PICTURE_CATEGORIES" :key="c" :class="{ active: filters.category === c }" @click="filters.category = c; resetAndLoad()">
            <span class="category-dot" :class="`tone-${index % 6}`"></span>{{ c }}
          </button>
        </div>
      </aside>

      <div class="content-area">
        <div class="content-toolbar">
          <div class="toolbar-tabs">
            <button class="tab" :class="{ active: filters.sort === 'time' }" @click="filters.sort = 'time'; resetAndLoad()">最新上传</button>
            <button class="tab" :class="{ active: filters.sort === 'popularity' }" @click="filters.sort = 'popularity'; resetAndLoad()">热门精选</button>
          </div>
          <div class="toolbar-actions">
            <span class="result-count">共 {{ pagination.total.toLocaleString() }} 张图片</span>
            <el-select v-model="filters.category" placeholder="全部分类" clearable class="category-select" @change="resetAndLoad">
              <el-option v-for="c in PICTURE_CATEGORIES" :key="c" :label="c" :value="c" />
            </el-select>
            <el-button @click="router.push('/pictures/my')"><el-icon><Folder /></el-icon>我的上传</el-button>
            <el-button type="primary" :icon="'Upload'" @click="openUpload">上传图片</el-button>
          </div>
        </div>
        <div class="chip-row">
          <button class="chip" :class="{ active: !filters.category }" @click="filters.category = ''; resetAndLoad()">全部</button>
          <button v-for="c in PICTURE_CATEGORIES.slice(0, 6)" :key="c" class="chip" :class="{ active: filters.category === c }" @click="filters.category = c; resetAndLoad()">{{ c }}</button>
        </div>

        <el-alert v-if="loadError" :title="loadError" type="warning" show-icon :closable="false" class="browse-error" />
        <div v-loading="loading" class="masonry">
          <PictureCard v-for="item in rows" :key="item.id" :item="item" />
        </div>
        <el-empty v-if="!loading && !loadError && rows.length === 0" description="暂无图片，试试调整筛选条件">
          <el-button type="primary" :icon="'Upload'" @click="openUpload">上传第一张图片</el-button>
        </el-empty>
        <div v-if="pagination.total > 0" class="pagination-wrap">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.itemsPerPage"
            :total="pagination.total"
            :page-sizes="[20, 40, 60]"
            layout="total, sizes, prev, pager, next"
            background
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </div>
    </section>

    <SiteFooter />

    <PictureUploadDialog v-model="uploadVisible" @success="load" />
  </div>
</template>

<style scoped>
.explore-page {
  position: relative;
  min-height: 100vh;
  background:
    radial-gradient(circle at 2% 48%, rgba(159,220,244,.13), transparent 22%),
    radial-gradient(circle at 98% 68%, rgba(236,114,150,.1), transparent 24%),
    linear-gradient(180deg, #fbfbfd, #f8f9fc 64%, #fbfbfd);
}
.explore-hero {
  min-height: 410px; position: relative; overflow: hidden; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 62px 24px 48px;
  background: radial-gradient(circle at 8% 10%, rgba(151,222,244,.55), transparent 32%),
    radial-gradient(circle at 92% 8%, rgba(249,175,197,.58), transparent 31%),
    linear-gradient(115deg, #e9f7fb, #fff8fa 58%, #fff);
}
.explore-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: .26;
  background-image: linear-gradient(rgba(255,255,255,.9) 1px, transparent 1px), linear-gradient(90deg,rgba(255,255,255,.9) 1px,transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(to bottom, #000, transparent 92%);
}
.explore-hero::after { content: ''; position: absolute; width: 280px; height: 280px; top: -150px; left: 42%; border-radius: 50%; background: rgba(255,255,255,.34); filter: blur(1px); animation: ambient-drift 9s ease-in-out infinite; }
.hero-copy { position: relative; z-index: 1; max-width: 680px; text-align: center; }
.hero-copy .eyebrow { display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px; border: 1px solid rgba(255,255,255,.7); border-radius: 999px; color: #aa647c; background: rgba(255,255,255,.44); font-size: 10px; font-weight: 800; letter-spacing: 2px; backdrop-filter: blur(10px); }
.hero-copy h1 { margin: 16px 0 11px; color: #171b22; font-size: clamp(40px, 5.3vw, 72px); line-height: 1.08; letter-spacing: -2.5px; font-weight: 900; text-shadow: 0 8px 28px rgba(72,79,98,.08); }
.hero-copy h1 em { color: transparent; background: linear-gradient(90deg,#d45f84,#ec7296 45%,#8a83cf); background-clip: text; -webkit-background-clip: text; font-style: normal; }
.hero-copy p { max-width: 520px; margin: 0 auto; color: #757d89; font-size: 14px; line-height: 1.8; }
.hero-search { width: min(760px, 92vw); height: 62px; margin-top: 30px; padding: 0 10px 0 20px; display: flex; align-items: center; gap: 12px; position: relative; z-index: 2; overflow: hidden; background: rgba(255,255,255,.88); border: 1px solid rgba(255,255,255,.95); border-radius: 19px; box-shadow: 0 18px 45px rgba(80,100,125,.13), inset 0 0 0 1px rgba(224,227,235,.68); backdrop-filter: blur(18px); transition: transform .3s cubic-bezier(.22,1,.36,1), box-shadow .3s ease; }
.hero-search::before { content: ''; position: absolute; width: 150px; height: 100%; left: -180px; top: 0; transform: skewX(-22deg); background: linear-gradient(90deg,transparent,rgba(255,255,255,.78),transparent); animation: search-sheen 5.5s ease-in-out infinite; pointer-events: none; }
.hero-search:focus-within { transform: translateY(-3px); box-shadow: 0 24px 52px rgba(97,91,122,.16), 0 0 0 4px rgba(236,114,150,.08); }
.hero-search > .el-icon { color: #242930; font-size: 21px; }
.hero-input { flex: 1; min-width: 0; }
.hero-input :deep(.el-input__wrapper) { box-shadow: none !important; background: transparent; padding: 0; }
.hero-input :deep(.el-input__inner) { font-size: 15px; }
.search-shortcut { padding: 5px 8px; color: #a1a7b0; background: #f3f4f7; border-radius: 6px; font-size: 11px; }
.search-submit { flex: 0 0 auto; width: 42px; height: 42px; border: 0; color: #fff; background: linear-gradient(135deg, #69bee1, var(--app-primary)); border-radius: 13px; box-shadow: 0 8px 18px rgba(236, 114, 150, 0.3); transition: transform 0.25s ease, box-shadow 0.25s ease; }
.search-submit:hover { transform: translateY(-2px) rotate(3deg); box-shadow: 0 12px 25px rgba(236, 114, 150, 0.42); }
.hero-meta { position: relative; z-index: 1; display: flex; align-items: center; flex-wrap: wrap; justify-content: center; gap: 14px; margin-top: 18px; color: #9298a3; font-size: 12px; }
.hero-meta strong { color: #b25370; font-size: 14px; font-weight: 900; }
.meta-separator { width: 4px; height: 4px; border-radius: 50%; background: #cad0d8; }
.text-link { display: inline-flex; align-items: center; gap: 5px; border: 0; background: transparent; color: #b4677e; font-size: 12px; font-weight: 700; cursor: pointer; }
.hero-orbit { position: absolute; border: 1px dashed rgba(255,255,255,.78); border-radius: 50%; pointer-events: none; animation: orbit-spin 28s linear infinite; }
.hero-orbit::after { content: ''; position: absolute; width: 13px; height: 13px; left: 22%; top: 4%; border-radius: 5px; background: rgba(236,114,150,.5); box-shadow: 0 0 0 7px rgba(255,255,255,.22); }
.orbit-one { width: 500px; height: 500px; left: -190px; top: -190px; }.orbit-two { width: 420px; height: 420px; right: -120px; bottom: -250px; animation-direction: reverse; animation-duration: 34s; }.orbit-two::after { background: rgba(98,196,233,.55); }
.hero-pixel-field { position: absolute; z-index: 1; inset: 0; pointer-events: none; }.hero-pixel-field i { position: absolute; width: 10px; height: 10px; border-radius: 3px; background: rgba(236,114,150,.38); animation: pixel-float 5s ease-in-out infinite; }.hero-pixel-field i:nth-child(1) { left: 7%; top: 28%; }.hero-pixel-field i:nth-child(2) { left: 14%; bottom: 17%; background: rgba(104,205,181,.5); animation-delay: -1s; }.hero-pixel-field i:nth-child(3) { left: 28%; top: 16%; width: 7px; height: 7px; background: rgba(155,137,223,.46); animation-delay: -2s; }.hero-pixel-field i:nth-child(4) { right: 7%; top: 26%; background: rgba(98,196,233,.48); }.hero-pixel-field i:nth-child(5) { right: 17%; bottom: 15%; width: 7px; height: 7px; animation-delay: -2.6s; }.hero-pixel-field i:nth-child(n+6) { display: none; }
.hero-visual-note { position: absolute; z-index: 1; display: flex; align-items: center; gap: 10px; padding: 11px 13px; border: 1px solid rgba(255,255,255,.82); border-radius: 16px; background: rgba(255,255,255,.5); box-shadow: 0 15px 35px rgba(70,81,102,.1); backdrop-filter: blur(14px); animation: note-float 6s ease-in-out infinite; }.hero-visual-note--left { left: max(3%, calc((100% - 1380px) / 2)); bottom: 70px; transform: rotate(-5deg); }.hero-visual-note--right { right: max(3%, calc((100% - 1380px) / 2)); top: 82px; transform: rotate(5deg); animation-delay: -3s; }.hero-visual-note > span:first-child { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 11px; color: #c85b7b; background: #fff0f5; }.hero-visual-note strong, .hero-visual-note small { display: block; }.hero-visual-note strong { color: #555b65; font-size: 10px; }.hero-visual-note small { margin-top: 3px; color: #a0a6af; font-size: 8px; }.note-dots { display: flex !important; align-items: flex-end; gap: 3px; }.note-dots i { width: 5px; border-radius: 5px; background: #75c8e7; }.note-dots i:nth-child(1) { height: 12px; }.note-dots i:nth-child(2) { height: 21px; background: #ed83a2; }.note-dots i:nth-child(3) { height: 27px; background: #9b89df; }
.workspace { width: min(1500px, 100%); margin: 0 auto; padding: 30px var(--app-page-x) 60px; display: flex; gap: 30px; }
.sidebar { position: sticky; top: 84px; width: 218px; flex: 0 0 218px; align-self: flex-start; padding: 20px 17px; border: 1px solid rgba(229,232,239,.86); border-radius: 21px; background: rgba(255,255,255,.68); box-shadow: 0 14px 38px rgba(48,54,68,.055); backdrop-filter: blur(15px); }
.sidebar-heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 22px; }
.section-kicker { color: #aa647c; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
.sidebar-heading h2 { margin: 8px 0 0; font-size: 20px; }
.side-menu { display: grid; gap: 6px; }
.side-menu-item { display: flex; align-items: center; gap: 10px; padding: 11px 12px; border: 0; border-radius: 11px; color: #68717d; background: transparent; text-align: left; font-size: 13px; cursor: pointer; transition: color .2s ease, background .2s ease, transform .2s ease; }.side-menu-item:hover { transform: translateX(3px); }.side-menu-item:hover, .side-menu-item.active { color: var(--app-ink); background: linear-gradient(90deg,#fff0f5,#f5f7fb); font-weight: 700; }.side-menu-item.active .el-icon { color: #d15f81; }
.side-divider { height: 1px; margin: 24px 0; background: var(--app-line); }
.sidebar-heading.compact { align-items: center; margin-bottom: 12px; color: #4e5660; font-size: 12px; font-weight: 700; }
.text-button { border: 0; background: transparent; color: #b4677e; font-size: 12px; cursor: pointer; }
.category-list { display: grid; gap: 3px; }
.category-list button { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border: 0; border-radius: 10px; background: transparent; color: #808895; text-align: left; font-size: 13px; cursor: pointer; transition: background .2s ease, transform .2s ease; }.category-list button:hover { transform: translateX(3px); }.category-list button:hover, .category-list button.active { color: var(--app-ink); background: #f6f7f9; }
.category-dot { width: 8px; height: 8px; border-radius: 3px; }
.tone-0 { background: #f49883; }.tone-1 { background: #b8aaf4; }.tone-2 { background: #91c9ed; }.tone-3 { background: #9ed9bf; }.tone-4 { background: #eac77c; }.tone-5 { background: #aab7c7; }
.content-area { min-width: 0; flex: 1; }
.content-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 5px 8px 5px 18px; border: 1px solid rgba(230,232,238,.9); border-radius: 18px; background: rgba(255,255,255,.76); box-shadow: 0 11px 30px rgba(44,49,63,.05); backdrop-filter: blur(14px); }
.toolbar-tabs { display: flex; gap: 24px; }
.tab { position: relative; padding: 12px 0 15px; border: 0; background: transparent; color: #989fa9; font-size: 14px; font-weight: 600; cursor: pointer; }
.tab.active, .tab:hover { color: var(--app-ink); }
.tab.active::after { content: ""; position: absolute; left: 0; right: 0; bottom: 4px; height: 3px; border-radius: 3px; background: linear-gradient(90deg,#ef83a3,#aa8edb); }
.content-toolbar .toolbar-actions { display: flex; align-items: center; gap: 8px; }
.result-count { color: #a2a8b1; font-size: 11px; }
.category-select { width: 145px; }
.chip-row { display: flex; gap: 8px; overflow-x: auto; padding: 17px 2px 20px; scrollbar-width: none; }
.chip-row::-webkit-scrollbar { display: none; }
.chip { flex: 0 0 auto; padding: 8px 13px; border: 1px solid var(--app-line); border-radius: 999px; background: rgba(255,255,255,.88); color: #737b86; font-size: 12px; cursor: pointer; transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease, background .2s ease; }.chip:hover { transform: translateY(-2px); }.chip:hover, .chip.active { color: #a54f6a; border-color: #efb5c6; background: #fff5f8; box-shadow: 0 7px 16px rgba(191,91,121,.09); }.chip.active { font-weight: 800; }
.browse-error { margin: 18px 0; border-radius: 15px; }.pagination-wrap { margin-top: 26px; display: flex; justify-content: center; }.masonry { min-height: 180px; }.masonry :deep(.pic-card) { border-color: rgba(231,233,239,.88) !important; box-shadow: 0 10px 27px rgba(40,45,58,.065) !important; animation: card-reveal .65s cubic-bezier(.22,1,.36,1) both; }.masonry :deep(.pic-card:hover) { box-shadow: 0 22px 46px rgba(48,54,69,.14) !important; }.masonry :deep(.pic-card .body) { background: linear-gradient(180deg,#fff,rgba(252,252,254,.98)); }.masonry :deep(.pic-card .name) { font-weight: 800; }.masonry :deep(.pic-card:nth-child(4n+2)) { animation-delay: 70ms; }.masonry :deep(.pic-card:nth-child(4n+3)) { animation-delay: 140ms; }.masonry :deep(.pic-card:nth-child(4n)) { animation-delay: 210ms; }.content-area :deep(.el-empty) { margin-top: 12px; border: 1px dashed #e1e4eb; border-radius: 22px; background: rgba(255,255,255,.65); }

@keyframes ambient-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(24px,14px); } }
@keyframes orbit-spin { to { transform: rotate(360deg); } }
@keyframes pixel-float { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-9px) rotate(11deg); } }
@keyframes note-float { 0%,100% { translate: 0 0; } 50% { translate: 0 -8px; } }
@keyframes search-sheen { 0%,55% { left: -180px; } 85%,100% { left: calc(100% + 60px); } }
@keyframes card-reveal { from { transform: translateY(14px); opacity: 0; } }

@media (max-width: 1080px) { .workspace { gap: 22px; } .sidebar { width: 190px; flex-basis: 190px; } .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); } }
@media (max-width: 1180px) { .hero-visual-note { display: none; } }
@media (max-width: 760px) {
  .explore-hero { min-height: 385px; padding: 56px 18px 36px; }
  .hero-copy h1 { font-size: 43px; }
  .workspace { display: block; padding: 23px 18px 45px; }
  .sidebar { position: static; width: auto; padding: 16px; }
  .sidebar-heading { align-items: center; margin-bottom: 12px; }
  .sidebar-heading > div { display: flex; align-items: baseline; gap: 9px; }
  .sidebar-heading h2 { margin: 0; font-size: 17px; }
  .side-menu { display: flex; overflow-x: auto; padding-bottom: 4px; }
  .side-menu-item { white-space: nowrap; }
  .side-divider, .sidebar-heading.compact, .category-list { display: none; }
  .content-area { margin-top: 25px; }
  .content-toolbar { align-items: flex-end; }
  .toolbar-tabs { gap: 16px; overflow-x: auto; }
  .tab { white-space: nowrap; font-size: 13px; }
  .result-count, .category-select { display: none; }
  .content-toolbar .toolbar-actions .el-button:first-of-type { display: none; }
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
}
@media (max-width: 390px) { .grid { grid-template-columns: 1fr; } }
@media (max-width: 480px) {
  .search-shortcut { display: none; }
  .hero-search { width: calc(100vw - 28px); height: 58px; margin-top: 24px; padding-left: 15px; }
  .hero-copy h1 { font-size: 38px; letter-spacing: -1.8px; }
  .hero-meta { gap: 9px; }
  .content-toolbar { padding-left: 13px; }
}
@media (prefers-reduced-motion: reduce) {
  .explore-hero::after, .hero-orbit, .hero-pixel-field i, .hero-visual-note, .hero-search::before, .masonry :deep(.pic-card) { animation: none; }
  .hero-search, .search-submit, .side-menu-item, .category-list button, .chip { transition: none; }
  .hero-search:focus-within, .search-submit:hover, .side-menu-item:hover, .category-list button:hover, .chip:hover { transform: none; }
}
</style>
