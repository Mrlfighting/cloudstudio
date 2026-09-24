<script setup lang="ts">
/**
 * 用户端图片列表：搜索 / 分类 / 排序 / 分页（登录用户可上传）
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { pictureApi } from '@/api/picture'
import { getErrorMessage } from '@/api/http'
import { PICTURE_CATEGORIES, type PictureListItemRead, type PictureSort } from '@/types/picture'
import PictureCard from '@/components/PictureCard.vue'
import PictureUploadDialog from '@/components/PictureUploadDialog.vue'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()

const loading = ref(false)
const rows = ref<PictureListItemRead[]>([])
const uploadVisible = ref(false)

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
    ElMessage.error(getErrorMessage(err, '获取图片列表失败'))
  } finally {
    loading.value = false
  }
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
            <el-button type="primary" :icon="'Upload'" @click="uploadVisible = true">上传图片</el-button>
          </div>
        </div>
        <div class="chip-row">
          <button class="chip" :class="{ active: !filters.category }" @click="filters.category = ''; resetAndLoad()">全部</button>
          <button v-for="c in PICTURE_CATEGORIES.slice(0, 6)" :key="c" class="chip" :class="{ active: filters.category === c }" @click="filters.category = c; resetAndLoad()">{{ c }}</button>
        </div>

        <div v-loading="loading" class="masonry">
          <PictureCard v-for="item in rows" :key="item.id" :item="item" />
        </div>
        <el-empty v-if="!loading && rows.length === 0" description="暂无图片，试试调整筛选条件">
          <el-button type="primary" :icon="'Upload'" @click="uploadVisible = true">上传第一张图片</el-button>
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
.toolbar-card {
  border-radius: 10px;
  margin-bottom: 20px;
}

.hero-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.eyebrow { color: #b16880; font-size: 11px; font-weight: 800; letter-spacing: 2px; margin-bottom: 10px; }
.page-title { margin-bottom: 0; }
.page-subtitle { margin: 10px 0 0; color: var(--app-muted); font-size: 15px; }
.hero-orb { width: 110px; height: 88px; position: relative; opacity: .9; }
.hero-orb::before, .hero-orb::after, .hero-orb span, .hero-orb i { content: ""; position: absolute; border-radius: 999px; }
.hero-orb::before { width: 68px; height: 68px; right: 12px; top: 5px; background: var(--app-blue); }
.hero-orb::after { width: 48px; height: 48px; right: 0; bottom: 0; background: var(--app-primary); opacity: .8; }
.hero-orb span { width: 34px; height: 34px; left: 10px; bottom: 8px; background: var(--app-lavender); }
.hero-orb i { width: 16px; height: 16px; left: 38px; top: 0; background: var(--app-mint); }

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.category-pills { display: flex; gap: 6px; flex-wrap: wrap; width: 100%; order: 5; }
.category-pills button { border: 1px solid var(--app-line); background: #fff; color: var(--app-text); border-radius: 999px; padding: 7px 14px; cursor: pointer; font-size: 12px; transition: .2s; }
.category-pills button:hover, .category-pills button.active { border-color: var(--app-primary); background: var(--app-primary-soft); color: #b85a78; }

.toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.search {
  width: 280px;
}

.category {
  width: 160px;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
@media (max-width: 560px) {
  .hero-orb { display: none; }
  .search, .category { width: 100%; }
  .toolbar-actions { width: 100%; margin-left: 0; }
  .toolbar-actions .el-button { flex: 1; }
}

.explore-page { min-height: 100vh; background: #fbfbfd; }
.explore-hero {
  min-height: 410px; position: relative; overflow: hidden; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 62px 24px 48px;
  background: radial-gradient(circle at 8% 10%, rgba(151,222,244,.55), transparent 32%),
    radial-gradient(circle at 92% 8%, rgba(249,175,197,.58), transparent 31%),
    linear-gradient(115deg, #e9f7fb, #fff8fa 58%, #fff);
}
.hero-copy { position: relative; z-index: 1; max-width: 680px; text-align: center; }
.hero-copy .eyebrow { display: inline-flex; align-items: center; gap: 7px; color: #aa647c; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
.hero-copy h1 { margin: 15px 0 10px; font-size: clamp(40px, 5.3vw, 72px); line-height: 1.08; font-weight: 800; }
.hero-copy h1 em { color: var(--app-primary); font-style: normal; }
.hero-copy p { max-width: 520px; margin: 0 auto; color: #757d89; font-size: 14px; line-height: 1.8; }
.hero-search { width: min(760px, 92vw); height: 62px; margin-top: 30px; padding: 0 10px 0 20px; display: flex; align-items: center; gap: 12px; position: relative; z-index: 1; background: rgba(255,255,255,.9); border: 1px solid rgba(226,228,236,.95); border-radius: 18px; box-shadow: 0 14px 34px rgba(80,100,125,.11); }
.hero-search > .el-icon { color: #242930; font-size: 21px; }
.hero-input { flex: 1; min-width: 0; }
.hero-input :deep(.el-input__wrapper) { box-shadow: none !important; background: transparent; padding: 0; }
.hero-input :deep(.el-input__inner) { font-size: 15px; }
.search-shortcut { padding: 5px 8px; color: #a1a7b0; background: #f3f4f7; border-radius: 6px; font-size: 11px; }
.search-submit { width: 42px; height: 42px; border: 0; color: #fff; background: linear-gradient(135deg, var(--app-blue), var(--app-primary)); border-radius: 12px; box-shadow: 0 8px 18px rgba(236, 114, 150, 0.3); transition: transform 0.2s ease, box-shadow 0.2s ease; }
.search-submit:hover { transform: translateY(-1px); box-shadow: 0 10px 22px rgba(236, 114, 150, 0.42); }
.hero-meta { position: relative; z-index: 1; display: flex; align-items: center; flex-wrap: wrap; justify-content: center; gap: 14px; margin-top: 18px; color: #9298a3; font-size: 12px; }
.hero-meta strong { color: #4f5661; }
.meta-separator { width: 4px; height: 4px; border-radius: 50%; background: #cad0d8; }
.text-link { display: inline-flex; align-items: center; gap: 5px; border: 0; background: transparent; color: #b4677e; font-size: 12px; font-weight: 700; cursor: pointer; }
.hero-orbit { position: absolute; border: 1px solid rgba(255,255,255,.65); border-radius: 50%; pointer-events: none; }
.orbit-one { width: 500px; height: 500px; left: -190px; top: -190px; }
.orbit-two { width: 420px; height: 420px; right: -120px; bottom: -250px; }
.workspace { width: min(1500px, 100%); margin: 0 auto; padding: 30px var(--app-page-x) 60px; display: flex; gap: 30px; }
.sidebar { width: 218px; flex: 0 0 218px; padding-top: 4px; }
.sidebar-heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 22px; }
.section-kicker { color: #aa647c; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
.sidebar-heading h2 { margin: 8px 0 0; font-size: 20px; }
.side-menu { display: grid; gap: 6px; }
.side-menu-item { display: flex; align-items: center; gap: 10px; padding: 11px 12px; border: 0; border-radius: 10px; color: #68717d; background: transparent; text-align: left; font-size: 13px; cursor: pointer; }
.side-menu-item:hover, .side-menu-item.active { color: var(--app-ink); background: #f2f3f7; font-weight: 700; }
.side-divider { height: 1px; margin: 24px 0; background: var(--app-line); }
.sidebar-heading.compact { align-items: center; margin-bottom: 12px; color: #4e5660; font-size: 12px; font-weight: 700; }
.text-button { border: 0; background: transparent; color: #b4677e; font-size: 12px; cursor: pointer; }
.category-list { display: grid; gap: 3px; }
.category-list button { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border: 0; border-radius: 9px; background: transparent; color: #808895; text-align: left; font-size: 13px; cursor: pointer; }
.category-list button:hover, .category-list button.active { color: var(--app-ink); background: #f6f7f9; }
.category-dot { width: 8px; height: 8px; border-radius: 3px; }
.tone-0 { background: #f49883; }.tone-1 { background: #b8aaf4; }.tone-2 { background: #91c9ed; }.tone-3 { background: #9ed9bf; }.tone-4 { background: #eac77c; }.tone-5 { background: #aab7c7; }
.content-area { min-width: 0; flex: 1; }
.content-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; border-bottom: 1px solid var(--app-line); }
.toolbar-tabs { display: flex; gap: 24px; }
.tab { position: relative; padding: 12px 0 15px; border: 0; background: transparent; color: #989fa9; font-size: 14px; font-weight: 600; cursor: pointer; }
.tab.active, .tab:hover { color: var(--app-ink); }
.tab.active::after { content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 3px; border-radius: 3px 3px 0 0; background: var(--app-primary); }
.content-toolbar .toolbar-actions { display: flex; align-items: center; gap: 8px; }
.result-count { color: #a2a8b1; font-size: 11px; }
.category-select { width: 145px; }
.chip-row { display: flex; gap: 8px; overflow-x: auto; padding: 18px 0 20px; scrollbar-width: none; }
.chip-row::-webkit-scrollbar { display: none; }
.chip { flex: 0 0 auto; padding: 8px 12px; border: 1px solid var(--app-line); border-radius: 999px; background: #fff; color: #737b86; font-size: 12px; cursor: pointer; }
.chip:hover, .chip.active { color: var(--app-ink); border-color: #d0d5dd; box-shadow: 0 3px 8px rgba(46,50,60,.05); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; align-items: start; min-height: 120px; }
@media (max-width: 1080px) { .workspace { gap: 22px; } .sidebar { width: 190px; flex-basis: 190px; } .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); } }
@media (max-width: 760px) {
  .explore-hero { min-height: 385px; padding: 56px 18px 36px; }
  .hero-copy h1 { font-size: 43px; }
  .workspace { display: block; padding: 23px 18px 45px; }
  .sidebar { width: auto; }
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
</style>
