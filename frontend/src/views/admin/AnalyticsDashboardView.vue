<script setup lang="ts">
/** 管理员数据中心：公共图库、空间与存储运营数据。 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Coin, Download, FolderOpened, PictureFilled } from '@element-plus/icons-vue'
import { graphic, type EChartsOption } from 'echarts'
import { analyticsApi } from '@/api/analytics'
import { getErrorMessage } from '@/api/http'
import { formatBytes } from '@/types/space'
import type {
  CategoryStat,
  GalleryOverview,
  Granularity,
  SpaceRankItem,
  SpacesOverview,
  StorageTrendPoint,
  TagStat,
  TopUploader,
  TrendPoint,
} from '@/types/analytics'
import BaseChart from '@/components/BaseChart.vue'
import StatCard from '@/components/StatCard.vue'

const router = useRouter()
const loading = ref(false)
const trendLoading = ref(false)
const rankingLoading = ref(false)
const loadFailed = ref(false)
const lastUpdated = ref('')

const galleryOverview = ref<GalleryOverview | null>(null)
const spacesOverview = ref<SpacesOverview | null>(null)
const category = ref<CategoryStat[]>([])
const tags = ref<TagStat[]>([])
const trend = ref<TrendPoint[]>([])
const storageTrend = ref<StorageTrendPoint[]>([])
const ranking = ref<SpaceRankItem[]>([])
const topUploaders = ref<TopUploader[]>([])

const granularity = ref<Granularity>('day')
const rankingSort = ref<'count' | 'size'>('count')
const palette = ['#ef7e9f', '#70cae9', '#69cbb5', '#a99be6', '#f3bd72', '#8ea9f0']
const categoryTotal = computed(() => category.value.reduce((sum, item) => sum + item.count, 0))

const adminShortcuts = [
  { title: '分析仪表盘', desc: '全站运营趋势', path: '/admin/analytics', icon: '01' },
  { title: '图片审核', desc: '维护公共内容', path: '/pictures/manage', icon: '02' },
  { title: '成员管理', desc: '用户与角色管理', path: '/admin/users', icon: '03' },
  { title: '空间管理', desc: '配额与状态管理', path: '/spaces/manage', icon: '04' },
] as const

function markUpdated(): void {
  lastUpdated.value = new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date())
}

async function loadAll() {
  loading.value = true
  loadFailed.value = false
  try {
    const [overview, spaces, cat, tagList, trendList, storageList, rankingList, topUploaderList] = await Promise.all([
      analyticsApi.galleryOverview(),
      analyticsApi.spacesOverview(),
      analyticsApi.galleryCategory(),
      analyticsApi.galleryTags(20),
      analyticsApi.galleryTrend(granularity.value),
      analyticsApi.galleryStorageTrend(granularity.value),
      analyticsApi.spacesRanking(10, rankingSort.value),
      analyticsApi.topUploaders(10),
    ])
    galleryOverview.value = overview
    spacesOverview.value = spaces
    category.value = cat
    tags.value = tagList
    trend.value = trendList
    storageTrend.value = storageList
    ranking.value = rankingList
    topUploaders.value = topUploaderList
    markUpdated()
  } catch (err) {
    loadFailed.value = true
    ElMessage.error(getErrorMessage(err, '获取分析数据失败'))
  } finally {
    loading.value = false
  }
}

async function reloadTrend() {
  trendLoading.value = true
  try {
    const [trendList, storageList] = await Promise.all([
      analyticsApi.galleryTrend(granularity.value),
      analyticsApi.galleryStorageTrend(granularity.value),
    ])
    trend.value = trendList
    storageTrend.value = storageList
    markUpdated()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取趋势数据失败'))
  } finally {
    trendLoading.value = false
  }
}

async function reloadRanking() {
  rankingLoading.value = true
  try {
    ranking.value = await analyticsApi.spacesRanking(10, rankingSort.value)
    markUpdated()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取空间排行失败'))
  } finally {
    rankingLoading.value = false
  }
}

const lineTooltip = {
  trigger: 'axis' as const,
  backgroundColor: 'rgba(255,255,255,.96)',
  borderColor: '#eceef3',
  borderWidth: 1,
  textStyle: { color: '#303641' },
  extraCssText: 'border-radius:12px;box-shadow:0 12px 30px rgba(39,45,58,.12);',
}

const axisStyle = {
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { color: '#9aa2ad', fontSize: 11 },
}

const trendOption = computed<EChartsOption>(() => ({
  animationDuration: 1100,
  animationEasing: 'cubicOut',
  tooltip: lineTooltip,
  grid: { left: 42, right: 22, top: 24, bottom: 34 },
  xAxis: { type: 'category', boundaryGap: false, data: trend.value.map((t) => t.period), ...axisStyle },
  yAxis: {
    type: 'value',
    minInterval: 1,
    ...axisStyle,
    splitLine: { lineStyle: { color: '#f0f2f6', type: 'dashed' } },
  },
  series: [{
    name: '上传数量',
    type: 'line',
    smooth: .42,
    showSymbol: false,
    symbolSize: 8,
    emphasis: { focus: 'series', scale: true },
    lineStyle: { width: 4, color: '#ef7e9f', shadowBlur: 12, shadowColor: 'rgba(239,126,159,.28)' },
    areaStyle: {
      color: new graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(239,126,159,.34)' },
        { offset: 1, color: 'rgba(239,126,159,.02)' },
      ]),
    },
    data: trend.value.map((t) => t.count),
  }],
}))

const storageOption = computed<EChartsOption>(() => ({
  animationDuration: 1200,
  animationEasing: 'cubicOut',
  tooltip: {
    ...lineTooltip,
    valueFormatter: (value) => formatBytes(Number(value)),
  },
  grid: { left: 58, right: 22, top: 24, bottom: 34 },
  xAxis: { type: 'category', boundaryGap: false, data: storageTrend.value.map((t) => t.period), ...axisStyle },
  yAxis: {
    type: 'value',
    ...axisStyle,
    axisLabel: { color: '#9aa2ad', fontSize: 11, formatter: (value: number) => formatBytes(value) },
    splitLine: { lineStyle: { color: '#f0f2f6', type: 'dashed' } },
  },
  series: [{
    name: '累计容量',
    type: 'line',
    smooth: .42,
    showSymbol: false,
    lineStyle: { width: 4, color: '#70cae9', shadowBlur: 12, shadowColor: 'rgba(112,202,233,.3)' },
    areaStyle: {
      color: new graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(112,202,233,.38)' },
        { offset: 1, color: 'rgba(112,202,233,.02)' },
      ]),
    },
    data: storageTrend.value.map((t) => t.total_size),
  }],
}))

const categoryOption = computed<EChartsOption>(() => ({
  animationDuration: 1000,
  animationEasing: 'cubicOut',
  color: palette,
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 张 · {d}%' },
  title: {
    text: categoryTotal.value.toLocaleString('zh-CN'),
    subtext: '图片总量',
    left: 'center',
    top: '38%',
    textStyle: { color: '#20242a', fontSize: 22, fontWeight: 800 },
    subtextStyle: { color: '#9aa2ad', fontSize: 11, lineHeight: 24 },
  },
  legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: '#77808d' } },
  series: [{
    type: 'pie',
    radius: ['55%', '75%'],
    center: ['50%', '45%'],
    avoidLabelOverlap: true,
    itemStyle: { borderColor: '#fff', borderWidth: 4, borderRadius: 8 },
    label: { show: false },
    emphasis: { scale: true, scaleSize: 8 },
    data: category.value.map((c) => ({ name: c.category, value: c.count })),
  }],
}))

const tagCloudOption = computed<EChartsOption>(() => ({
  animationDuration: 900,
  tooltip: { show: true, formatter: '{b} · {c} 次' },
  series: [{
    type: 'wordCloud',
    shape: 'circle',
    left: 'center',
    top: 'center',
    width: '94%',
    height: '94%',
    sizeRange: [13, 44],
    rotationRange: [-12, 12],
    gridSize: 9,
    drawOutOfBound: false,
    textStyle: { fontFamily: 'sans-serif', fontWeight: 'bold' },
    emphasis: { textStyle: { shadowBlur: 14, shadowColor: 'rgba(50,55,70,.2)' } },
    data: tags.value.map((tag, index) => ({
      name: tag.tag,
      value: tag.count,
      textStyle: { color: palette[index % palette.length] },
    })),
  }],
}) as unknown as EChartsOption)

const rankingOption = computed<EChartsOption>(() => {
  const isCount = rankingSort.value === 'count'
  const data = ranking.value.map((item) => isCount ? item.total_count : Number((item.total_size / 1024 / 1024).toFixed(2)))
  return {
    animationDuration: 900,
    animationDelay: (index: number) => index * 55,
    tooltip: lineTooltip,
    grid: { left: 116, right: 48, top: 8, bottom: 28 },
    xAxis: {
      type: 'value',
      ...axisStyle,
      splitLine: { lineStyle: { color: '#f1f3f6', type: 'dashed' } },
    },
    yAxis: { type: 'category', data: ranking.value.map((item) => item.name), inverse: true, ...axisStyle },
    series: [{
      name: isCount ? '图片数' : '容量(MB)',
      type: 'bar',
      data,
      barMaxWidth: 18,
      itemStyle: {
        borderRadius: [0, 10, 10, 0],
        color: new graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#b9e8f8' },
          { offset: 1, color: '#70cae9' },
        ]),
      },
      emphasis: { itemStyle: { shadowBlur: 16, shadowColor: 'rgba(112,202,233,.35)' } },
      label: { show: true, position: 'right', color: '#66707c', fontWeight: 700 },
    }],
  }
})

const topUploadersOption = computed<EChartsOption>(() => ({
  animationDuration: 900,
  animationDelay: (index: number) => index * 55,
  tooltip: lineTooltip,
  grid: { left: 116, right: 48, top: 8, bottom: 28 },
  xAxis: {
    type: 'value',
    minInterval: 1,
    ...axisStyle,
    splitLine: { lineStyle: { color: '#f1f3f6', type: 'dashed' } },
  },
  yAxis: { type: 'category', data: topUploaders.value.map((item) => item.name || item.username), inverse: true, ...axisStyle },
  series: [{
    name: '上传数',
    type: 'bar',
    data: topUploaders.value.map((item) => item.count),
    barMaxWidth: 18,
    itemStyle: {
      borderRadius: [0, 10, 10, 0],
      color: new graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#f5bfd0' },
        { offset: 1, color: '#ef7e9f' },
      ]),
    },
    emphasis: { itemStyle: { shadowBlur: 16, shadowColor: 'rgba(239,126,159,.34)' } },
    label: { show: true, position: 'right', color: '#66707c', fontWeight: 700 },
  }],
}))

onMounted(loadAll)
</script>

<template>
  <main class="analytics-page" v-loading="loading">
    <span class="analytics-orb analytics-orb--blue" aria-hidden="true"></span>
    <span class="analytics-orb analytics-orb--pink" aria-hidden="true"></span>

    <header class="analytics-hero analytics-reveal">
      <div>
        <div class="analytics-eyebrow"><span></span> ADMIN · 数据中心</div>
        <h1>洞察每一次增长</h1>
        <p>公共图库、创作者与空间运营数据一览。</p>
      </div>
      <div class="analytics-hero__actions">
        <span v-if="lastUpdated" class="update-time"><i></i> 更新于 {{ lastUpdated }}</span>
        <el-button :loading="loading" @click="loadAll">
          <el-icon><Refresh /></el-icon>刷新数据
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="loadFailed"
      class="analytics-alert"
      title="部分分析数据暂时无法加载"
      description="请检查网络连接后重新刷新。"
      type="error"
      show-icon
      :closable="false"
    />

    <nav class="analytics-shortcuts analytics-reveal" aria-label="管理快捷入口">
      <button
        v-for="item in adminShortcuts"
        :key="item.path"
        class="analytics-shortcut"
        :class="{ active: $route.path === item.path }"
        @click="router.push(item.path)"
      >
        <span class="analytics-shortcut__index">{{ item.icon }}</span>
        <span><strong>{{ item.title }}</strong><small>{{ item.desc }}</small></span>
        <el-icon><ArrowRight /></el-icon>
      </button>
    </nav>

    <section class="analytics-stat-grid" aria-label="核心指标">
      <StatCard label="图片总数" :value="galleryOverview?.total_pictures ?? 0" description="公共图库已收录内容" :icon="PictureFilled" :delay="80" />
      <StatCard label="总容量" :value="formatBytes(galleryOverview?.total_size)" description="当前图库累计存储" :icon="Coin" accent="sky" :delay="140" />
      <StatCard label="总下载量" :value="galleryOverview?.total_downloads ?? 0" description="全站累计下载次数" :icon="Download" accent="mint" :delay="200" />
      <StatCard label="空间总数" :value="spacesOverview?.total_spaces ?? 0" description="已创建的用户空间" :icon="FolderOpened" accent="lavender" :delay="260" />
    </section>

    <section class="analytics-dashboard-grid">
      <article class="analytics-panel panel-trend analytics-reveal" style="--reveal-delay: 300ms">
        <header class="analytics-panel__head">
          <div><h2>素材增长趋势</h2><p>观察不同时段的图片上传变化</p></div>
          <el-radio-group v-model="granularity" size="small" @change="reloadTrend">
            <el-radio-button value="day">日</el-radio-button>
            <el-radio-button value="week">周</el-radio-button>
            <el-radio-button value="month">月</el-radio-button>
          </el-radio-group>
        </header>
        <div v-loading="trendLoading" class="analytics-chart-body">
          <BaseChart v-if="trend.length" :option="trendOption" height="330px" aria-label="公共图库上传趋势折线图" />
          <el-empty v-else description="暂无趋势数据" />
        </div>
      </article>

      <article class="analytics-panel panel-category analytics-reveal" style="--reveal-delay: 360ms">
        <header class="analytics-panel__head"><div><h2>分类占比</h2><p>图库内容结构分布</p></div></header>
        <BaseChart v-if="category.length" :option="categoryOption" height="330px" aria-label="公共图库分类占比环形图" />
        <el-empty v-else description="暂无分类数据" />
      </article>

      <article class="analytics-panel panel-tags analytics-reveal" style="--reveal-delay: 420ms">
        <header class="analytics-panel__head"><div><h2>热门标签</h2><p>当前素材内容关键词</p></div></header>
        <BaseChart v-if="tags.length" :option="tagCloudOption" height="320px" aria-label="公共图库热门标签词云" />
        <el-empty v-else description="暂无标签数据" />
      </article>

      <article class="analytics-panel panel-ranking analytics-reveal" style="--reveal-delay: 480ms">
        <header class="analytics-panel__head">
          <div><h2>空间排行榜</h2><p>空间活跃度 TOP 10</p></div>
          <el-radio-group v-model="rankingSort" size="small" @change="reloadRanking">
            <el-radio-button value="count">图片数</el-radio-button>
            <el-radio-button value="size">容量</el-radio-button>
          </el-radio-group>
        </header>
        <div v-loading="rankingLoading" class="analytics-chart-body">
          <BaseChart v-if="ranking.length" :option="rankingOption" height="320px" aria-label="空间排行榜柱状图" />
          <el-empty v-else description="暂无空间数据" />
        </div>
      </article>

      <article class="analytics-panel panel-uploaders analytics-reveal" style="--reveal-delay: 540ms">
        <header class="analytics-panel__head"><div><h2>活跃上传者</h2><p>内容贡献数量 TOP 10</p></div></header>
        <BaseChart v-if="topUploaders.length" :option="topUploadersOption" height="320px" aria-label="上传者排行榜柱状图" />
        <el-empty v-else description="暂无上传数据" />
      </article>

      <article class="analytics-panel panel-storage analytics-reveal" style="--reveal-delay: 600ms">
        <header class="analytics-panel__head"><div><h2>存储增长趋势</h2><p>累计存储容量随时间变化</p></div></header>
        <div v-loading="trendLoading" class="analytics-chart-body">
          <BaseChart v-if="storageTrend.length" :option="storageOption" height="300px" aria-label="图库存储增长趋势折线图" />
          <el-empty v-else description="暂无趋势数据" />
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.analytics-dashboard-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
}
.panel-trend { grid-column: span 8; }
.panel-category { grid-column: span 4; }
.panel-tags { grid-column: span 4; }
.panel-ranking { grid-column: span 8; }
.panel-uploaders { grid-column: span 6; }
.panel-storage { grid-column: span 6; }

@media (max-width: 1100px) {
  .panel-trend, .panel-category, .panel-tags, .panel-ranking, .panel-uploaders, .panel-storage { grid-column: span 6; }
}
@media (max-width: 720px) {
  .analytics-dashboard-grid { grid-template-columns: 1fr; }
  .panel-trend, .panel-category, .panel-tags, .panel-ranking, .panel-uploaders, .panel-storage { grid-column: auto; }
}
</style>
