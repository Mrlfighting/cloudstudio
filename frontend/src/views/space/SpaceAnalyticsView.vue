<script setup lang="ts">
/** 个人空间分析：配额、内容结构、上传趋势与热门图片。 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Coin, DataLine, PictureFilled, PieChart } from '@element-plus/icons-vue'
import { graphic, type EChartsOption } from 'echarts'
import { analyticsApi } from '@/api/analytics'
import { getErrorMessage } from '@/api/http'
import { formatBytes } from '@/types/space'
import type { CategoryStat, Granularity, MySpaceOverview, MyTopPicture, TagStat, TrendPoint } from '@/types/analytics'
import BaseChart from '@/components/BaseChart.vue'
import StatCard from '@/components/StatCard.vue'

const router = useRouter()
const loading = ref(false)
const trendLoading = ref(false)
const loadFailed = ref(false)
const lastUpdated = ref('')
const overview = ref<MySpaceOverview | null>(null)
const trend = ref<TrendPoint[]>([])
const category = ref<CategoryStat[]>([])
const tags = ref<TagStat[]>([])
const topPictures = ref<MyTopPicture[]>([])
const granularity = ref<Granularity>('day')
const palette = ['#ef7e9f', '#70cae9', '#69cbb5', '#a99be6', '#f3bd72', '#8ea9f0']

const hasSpace = computed(() => overview.value?.space_id != null)
const remainingCount = computed(() => Math.max(0, (overview.value?.max_count ?? 0) - (overview.value?.picture_count ?? 0)))
const categoryTotal = computed(() => category.value.reduce((sum, item) => sum + item.count, 0))

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
    const [ov, trendList, cat, tagList, topList] = await Promise.all([
      analyticsApi.myOverview(),
      analyticsApi.myTrend(granularity.value),
      analyticsApi.myCategory(),
      analyticsApi.myTags(20),
      analyticsApi.myTopPictures(10),
    ])
    overview.value = ov
    trend.value = trendList
    category.value = cat
    tags.value = tagList
    topPictures.value = topList
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
    trend.value = await analyticsApi.myTrend(granularity.value)
    markUpdated()
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取趋势数据失败'))
  } finally {
    trendLoading.value = false
  }
}

function sizePercent(): number {
  if (!overview.value) return 0
  return Math.min(100, Math.round((overview.value.size_usage ?? 0) * 100))
}

function countPercent(): number {
  if (!overview.value) return 0
  return Math.min(100, Math.round((overview.value.count_usage ?? 0) * 100))
}

const tooltipStyle = {
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
  tooltip: tooltipStyle,
  grid: { left: 42, right: 22, top: 24, bottom: 34 },
  xAxis: { type: 'category', boundaryGap: false, data: trend.value.map((item) => item.period), ...axisStyle },
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
    lineStyle: { width: 4, color: '#ef7e9f', shadowBlur: 12, shadowColor: 'rgba(239,126,159,.28)' },
    areaStyle: {
      color: new graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(239,126,159,.34)' },
        { offset: 1, color: 'rgba(239,126,159,.02)' },
      ]),
    },
    emphasis: { focus: 'series' },
    data: trend.value.map((item) => item.count),
  }],
}))

const categoryOption = computed<EChartsOption>(() => ({
  animationDuration: 1000,
  animationEasing: 'cubicOut',
  color: palette,
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 张 · {d}%' },
  title: {
    text: categoryTotal.value.toLocaleString('zh-CN'),
    subtext: '空间图片',
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
    itemStyle: { borderColor: '#fff', borderWidth: 4, borderRadius: 8 },
    label: { show: false },
    emphasis: { scale: true, scaleSize: 8 },
    data: category.value.map((item) => ({ name: item.category, value: item.count })),
  }],
}))

const tagsOption = computed<EChartsOption>(() => ({
  animationDuration: 900,
  animationDelay: (index: number) => index * 45,
  tooltip: tooltipStyle,
  grid: { left: 84, right: 44, top: 8, bottom: 28 },
  xAxis: {
    type: 'value',
    minInterval: 1,
    ...axisStyle,
    splitLine: { lineStyle: { color: '#f1f3f6', type: 'dashed' } },
  },
  yAxis: { type: 'category', data: tags.value.map((item) => item.tag), inverse: true, ...axisStyle },
  series: [{
    name: '使用次数',
    type: 'bar',
    data: tags.value.map((item) => item.count),
    barMaxWidth: 17,
    itemStyle: {
      borderRadius: [0, 10, 10, 0],
      color: new graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#c9eee6' },
        { offset: 1, color: '#69cbb5' },
      ]),
    },
    emphasis: { itemStyle: { shadowBlur: 16, shadowColor: 'rgba(105,203,181,.32)' } },
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
        <div class="analytics-eyebrow"><span></span> INSIGHTS · 我的数据</div>
        <h1>看见你的创作轨迹</h1>
        <p>从空间使用到内容偏好，了解每一次积累。</p>
      </div>
      <div class="analytics-hero__actions">
        <span v-if="lastUpdated" class="update-time"><i></i> 更新于 {{ lastUpdated }}</span>
        <el-button :loading="loading" @click="loadAll"><el-icon><Refresh /></el-icon>刷新数据</el-button>
      </div>
    </header>

    <el-alert
      v-if="loadFailed"
      class="analytics-alert"
      title="空间分析数据暂时无法加载"
      description="请检查网络连接后重新刷新。"
      type="error"
      show-icon
      :closable="false"
    />

    <section v-if="!loading && overview && !hasSpace" class="analytics-empty analytics-reveal">
      <div class="analytics-empty__icon"><el-icon><DataAnalysis /></el-icon></div>
      <h2>创建空间，开始记录创作数据</h2>
      <p>空间创建后，这里将展示容量使用、上传趋势、分类分布与热门图片。</p>
      <el-button type="primary" size="large" @click="router.push('/spaces')">前往我的空间</el-button>
    </section>

    <template v-else-if="overview">
      <section class="analytics-stat-grid" aria-label="空间核心指标">
        <StatCard label="图片数量" :value="overview.picture_count" :hint="`/ ${overview.max_count}`" description="当前空间已保存内容" :icon="PictureFilled" :delay="80" />
        <StatCard label="已用容量" :value="formatBytes(overview.total_size)" :hint="`/ ${formatBytes(overview.max_size)}`" description="空间存储使用情况" :icon="Coin" accent="sky" :delay="140" />
        <StatCard label="剩余配额" :value="remainingCount" description="还可继续保存的图片数" :icon="DataLine" accent="mint" :delay="200" />
        <StatCard label="容量使用率" :value="sizePercent()" hint="%" description="基于当前空间容量上限" :icon="PieChart" accent="lavender" :delay="260" />
      </section>

      <section class="space-analytics-grid">
        <article class="analytics-panel quota-panel analytics-reveal" style="--reveal-delay: 300ms">
          <header class="analytics-panel__head"><div><h2>空间健康度</h2><p>容量与图片数量配额</p></div><span class="health-dot">运行良好</span></header>
          <div class="quota-stack">
            <div class="quota-item">
              <div class="quota-label"><span>容量使用</span><strong>{{ sizePercent() }}%</strong></div>
              <el-progress :percentage="sizePercent()" :show-text="false" :stroke-width="10" :status="sizePercent() >= 100 ? 'exception' : undefined" />
              <div class="quota-text">{{ formatBytes(overview.total_size) }} / {{ formatBytes(overview.max_size) }}</div>
            </div>
            <div class="quota-item">
              <div class="quota-label"><span>图片数量</span><strong>{{ countPercent() }}%</strong></div>
              <el-progress :percentage="countPercent()" :show-text="false" :stroke-width="10" :status="countPercent() >= 100 ? 'exception' : undefined" />
              <div class="quota-text">{{ overview.picture_count }} / {{ overview.max_count }} 张</div>
            </div>
          </div>
        </article>

        <article class="analytics-panel trend-panel analytics-reveal" style="--reveal-delay: 360ms">
          <header class="analytics-panel__head">
            <div><h2>上传趋势</h2><p>你的素材积累节奏</p></div>
            <el-radio-group v-model="granularity" size="small" @change="reloadTrend">
              <el-radio-button value="day">日</el-radio-button>
              <el-radio-button value="week">周</el-radio-button>
              <el-radio-button value="month">月</el-radio-button>
            </el-radio-group>
          </header>
          <div v-loading="trendLoading" class="analytics-chart-body">
            <BaseChart v-if="trend.length" :option="trendOption" height="310px" aria-label="个人空间上传趋势折线图" />
            <el-empty v-else description="暂无上传记录" />
          </div>
        </article>

        <article class="analytics-panel category-panel analytics-reveal" style="--reveal-delay: 420ms">
          <header class="analytics-panel__head"><div><h2>分类占比</h2><p>空间内容结构分布</p></div></header>
          <BaseChart v-if="category.length" :option="categoryOption" height="320px" aria-label="个人空间分类占比环形图" />
          <el-empty v-else description="暂无分类数据" />
        </article>

        <article class="analytics-panel tags-panel analytics-reveal" style="--reveal-delay: 480ms">
          <header class="analytics-panel__head"><div><h2>标签偏好</h2><p>最常使用的内容关键词</p></div></header>
          <BaseChart v-if="tags.length" :option="tagsOption" height="320px" aria-label="个人空间标签排行柱状图" />
          <el-empty v-else description="暂无标签数据" />
        </article>

        <article class="analytics-panel hot-panel analytics-reveal" style="--reveal-delay: 540ms">
          <header class="analytics-panel__head"><div><h2>热门图片</h2><p>下载次数 TOP 10</p></div></header>
          <el-empty v-if="!topPictures.length" description="暂无图片" />
          <ol v-else class="hot-list">
            <li v-for="(picture, index) in topPictures" :key="picture.picture_id" class="hot-item">
              <span class="rank" :class="{ top: index < 3 }">{{ String(index + 1).padStart(2, '0') }}</span>
              <el-image class="hot-thumb" :src="picture.url" fit="cover" :preview-src-list="[picture.url]" preview-teleported />
              <span class="hot-copy"><strong>{{ picture.name }}</strong><small>空间素材</small></span>
              <span class="hot-count"><el-icon><Download /></el-icon>{{ picture.download_count }}</span>
            </li>
          </ol>
        </article>
      </section>
    </template>
  </main>
</template>

<style scoped>
.space-analytics-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 18px;
}
.quota-panel { grid-column: span 4; }
.trend-panel { grid-column: span 8; }
.category-panel { grid-column: span 5; }
.tags-panel { grid-column: span 7; }
.hot-panel { grid-column: 1 / -1; }
.quota-stack { display: grid; gap: 34px; padding: 24px 2px 16px; }
.quota-item { padding: 18px; border: 1px solid #f0f1f5; border-radius: 18px; background: linear-gradient(145deg, #fbfcfe, #fff); }
.quota-label { display: flex; align-items: center; justify-content: space-between; margin-bottom: 13px; color: #626c79; font-size: 13px; font-weight: 700; }
.quota-label strong { color: #242930; font-size: 18px; font-weight: 900; }
.quota-text { margin-top: 10px; color: #9aa2ad; font-size: 12px; }
.health-dot { display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px; border-radius: 999px; color: #378c75; background: #eaf8f4; font-size: 11px; font-weight: 800; }
.health-dot::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #51b99d; box-shadow: 0 0 0 5px rgba(81,185,157,.12); animation: health-pulse 2.4s ease-in-out infinite; }
.hot-list { list-style: none; margin: 0; padding: 4px 0 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 11px; }
.hot-item { display: flex; align-items: center; gap: 13px; min-width: 0; padding: 11px 13px; border: 1px solid #eff1f5; border-radius: 16px; background: linear-gradient(145deg, #fbfcfe, #fff); transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease; }
.hot-item:hover { transform: translateY(-4px); border-color: #f2bdcd; box-shadow: 0 14px 28px rgba(41,45,58,.09); }
.rank { width: 30px; flex-shrink: 0; color: #a0a8b3; font-size: 12px; font-weight: 900; font-variant-numeric: tabular-nums; }
.rank.top { color: #e5678c; }
.hot-thumb { width: 54px; height: 54px; flex-shrink: 0; border-radius: 13px; }
.hot-copy { min-width: 0; flex: 1; }
.hot-copy strong { display: block; overflow: hidden; color: #343a44; font-size: 14px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.hot-copy small { display: block; margin-top: 5px; color: #a2a9b3; font-size: 11px; }
.hot-count { display: inline-flex; align-items: center; gap: 5px; flex-shrink: 0; color: #8c95a1; font-size: 12px; font-weight: 700; }
@keyframes health-pulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }

@media (max-width: 1050px) {
  .quota-panel, .trend-panel, .category-panel, .tags-panel { grid-column: span 6; }
}
@media (max-width: 720px) {
  .space-analytics-grid { grid-template-columns: 1fr; }
  .quota-panel, .trend-panel, .category-panel, .tags-panel, .hot-panel { grid-column: auto; }
  .hot-list { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .health-dot::before { animation: none; }
  .hot-item:hover { transform: none; }
}
</style>
