<script setup lang="ts">
/**
 * 管理员分析仪表盘：公共图库 + 空间大盘可视化
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { EChartsOption } from 'echarts'
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
import PageIntro from '@/components/PageIntro.vue'
import StatCard from '@/components/StatCard.vue'

const loading = ref(false)
const trendLoading = ref(false)
const rankingLoading = ref(false)
const router = useRouter()

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

async function loadAll() {
  loading.value = true
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
  } catch (err) {
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
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取空间排行失败'))
  } finally {
    rankingLoading.value = false
  }
}

// ---- 图表 option ----

const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: trend.value.map((t) => t.period) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'line', smooth: true, data: trend.value.map((t) => t.count) }],
}))

const storageOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: storageTrend.value.map((t) => t.period) },
  yAxis: { type: 'value' },
  series: [
    { type: 'line', smooth: true, areaStyle: {}, data: storageTrend.value.map((t) => t.total_size) },
  ],
}))

const categoryOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} 张 ({d}%)' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['40%', '68%'],
      center: ['50%', '45%'],
      data: category.value.map((c) => ({ name: c.category, value: c.count })),
      label: { formatter: '{b}\n{d}%' },
    },
  ],
}))

const tagCloudOption = computed<EChartsOption>(
  () =>
    ({
      series: [
        {
          type: 'wordCloud',
          shape: 'circle',
          left: 'center',
          top: 'center',
          width: '90%',
          height: '90%',
          sizeRange: [12, 48],
          rotationRange: [0, 0],
          gridSize: 8,
          drawOutOfBound: false,
          textStyle: { fontFamily: 'sans-serif', fontWeight: 'bold' },
          data: tags.value.map((t) => ({ name: t.tag, value: t.count })),
        },
      ],
    }) as unknown as EChartsOption,
)

const rankingOption = computed<EChartsOption>(() => {
  const isCount = rankingSort.value === 'count'
  const data = ranking.value.map((r) =>
    isCount ? r.total_count : Number((r.total_size / 1024 / 1024).toFixed(2)),
  )
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 130, right: 40, top: 10, bottom: 30 },
    xAxis: { type: 'value', name: isCount ? '图片数' : '容量(MB)' },
    yAxis: { type: 'category', data: ranking.value.map((r) => r.name), inverse: true },
    series: [{ type: 'bar', data, barMaxWidth: 24, label: { show: true, position: 'right' } }],
  }
})

const topUploadersOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 130, right: 40, top: 10, bottom: 30 },
  xAxis: { type: 'value', name: '上传数', minInterval: 1 },
  yAxis: {
    type: 'category',
    data: topUploaders.value.map((u) => u.name || u.username),
    inverse: true,
  },
  series: [
    {
      type: 'bar',
      data: topUploaders.value.map((u) => u.count),
      barMaxWidth: 24,
      label: { show: true, position: 'right' },
    },
  ],
}))

onMounted(loadAll)

const adminShortcuts = [
  {
    title: '分析仪表盘',
    desc: '查看全站图片、空间与存储趋势',
    path: '/admin/analytics',
  },
  {
    title: '图片审核管理',
    desc: '审核公共图库内容并维护图片信息',
    path: '/pictures/manage',
  },
  {
    title: '成员管理',
    desc: '维护用户状态、角色与会员信息',
    path: '/admin/users',
  },
  {
    title: '空间管理',
    desc: '查看空间配额、状态并处理异常空间',
    path: '/spaces/manage',
  },
] as const
</script>

<template>
  <div class="dashboard-container" v-loading="loading">
    <PageIntro eyebrow="ADMIN · 数据总览" title="分析仪表盘" subtitle="公共图库与空间运营数据总览" />

    <el-card class="admin-quick-card" shadow="never">
      <div class="admin-quick-head">
        <div>
          <div class="admin-quick-title">管理入口</div>
          <div class="admin-quick-desc">常用后台页面快速跳转</div>
        </div>
      </div>
      <div class="admin-quick-grid">
        <button
          v-for="item in adminShortcuts"
          :key="item.path"
          class="admin-quick-item"
          :class="{ active: $route.path === item.path }"
          @click="router.push(item.path)"
        >
          <strong>{{ item.title }}</strong>
          <span>{{ item.desc }}</span>
        </button>
      </div>
    </el-card>

    <!-- 顶部统计卡片 -->
    <div class="stat-grid">
      <StatCard label="图片总数" :value="galleryOverview?.total_pictures ?? 0" />
      <StatCard label="总容量" :value="formatBytes(galleryOverview?.total_size)" />
      <StatCard label="总下载量" :value="galleryOverview?.total_downloads ?? 0" />
      <StatCard label="空间总数" :value="spacesOverview?.total_spaces ?? 0" />
    </div>

    <!-- 上传趋势 -->
    <el-card class="chart-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>上传趋势</span>
          <el-radio-group v-model="granularity" size="small" @change="reloadTrend">
            <el-radio-button value="day">日</el-radio-button>
            <el-radio-button value="week">周</el-radio-button>
            <el-radio-button value="month">月</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div v-loading="trendLoading">
        <BaseChart v-if="trend.length" :option="trendOption" />
        <el-empty v-else description="暂无趋势数据" />
      </div>
    </el-card>

    <!-- 分类分布 + 热门标签 -->
    <div class="chart-row">
      <el-card class="chart-card" shadow="never">
        <template #header><span>分类分布</span></template>
        <BaseChart v-if="category.length" :option="categoryOption" />
        <el-empty v-else description="暂无分类数据" />
      </el-card>
      <el-card class="chart-card" shadow="never">
        <template #header><span>热门标签</span></template>
        <BaseChart v-if="tags.length" :option="tagCloudOption" />
        <el-empty v-else description="暂无标签数据" />
      </el-card>
    </div>

    <!-- 空间排行榜 -->
    <el-card class="chart-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>空间排行榜 TOP 10</span>
          <el-radio-group v-model="rankingSort" size="small" @change="reloadRanking">
            <el-radio-button value="count">按图片数</el-radio-button>
            <el-radio-button value="size">按容量</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div v-loading="rankingLoading">
        <BaseChart v-if="ranking.length" :option="rankingOption" />
        <el-empty v-else description="暂无空间数据" />
      </div>
    </el-card>

    <!-- 上传者排行 -->
    <el-card class="chart-card" shadow="never">
      <template #header><span>上传者排行 TOP 10</span></template>
      <BaseChart v-if="topUploaders.length" :option="topUploadersOption" />
      <el-empty v-else description="暂无上传数据" />
    </el-card>

    <!-- 存储增长趋势 -->
    <el-card class="chart-card" shadow="never">
      <template #header><span>存储增长趋势</span></template>
      <div v-loading="trendLoading">
        <BaseChart v-if="storageTrend.length" :option="storageOption" />
        <el-empty v-else description="暂无趋势数据" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard-container {
  max-width: 1500px;
  margin: 0 auto;
  padding: 34px clamp(18px, 4.6vw, 68px) 64px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.admin-quick-card {
  border-radius: var(--app-radius-lg) !important;
  margin-bottom: 20px;
  border: 1px solid var(--app-line) !important;
  box-shadow: var(--app-shadow-soft) !important;
}

.admin-quick-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.admin-quick-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--app-ink);
}

.admin-quick-desc {
  margin-top: 6px;
  color: var(--app-muted);
  font-size: 13px;
}

.admin-quick-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.admin-quick-item {
  border: 1px solid var(--app-line-soft);
  border-radius: 18px;
  background: linear-gradient(145deg, #fff, #fafbfd);
  padding: 16px 18px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.admin-quick-item:hover {
  transform: translateY(-2px);
  border-color: #f2bdcd;
  box-shadow: 0 12px 26px rgba(38, 42, 52, 0.08);
}

.admin-quick-item.active {
  border-color: var(--app-primary);
  background: var(--app-primary-soft);
}

.admin-quick-item strong {
  display: block;
  color: var(--app-ink);
  font-size: 15px;
  font-weight: 800;
}

.admin-quick-item span {
  display: block;
  margin-top: 8px;
  color: var(--app-muted);
  font-size: 12px;
  line-height: 1.6;
}

.stat-card {
  border-radius: var(--app-radius-lg) !important;
  text-align: center;
  border: 1px solid var(--app-line) !important;
  box-shadow: var(--app-shadow-soft) !important;
}

.stat-label {
  font-size: 13px;
  color: var(--app-muted);
}

.stat-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 900;
  color: var(--app-ink);
}

.chart-card {
  border-radius: var(--app-radius-lg) !important;
  margin-bottom: 20px;
  border: 1px solid var(--app-line) !important;
  box-shadow: var(--app-shadow-soft) !important;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 900px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .chart-row {
    grid-template-columns: 1fr;
  }
  .admin-quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
