<script setup lang="ts">
/**
 * 管理员分析仪表盘：公共图库 + 空间大盘可视化
 */
import { computed, onMounted, ref } from 'vue'
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
  TrendPoint,
} from '@/types/analytics'
import BaseChart from '@/components/BaseChart.vue'

const loading = ref(false)
const trendLoading = ref(false)
const rankingLoading = ref(false)

const galleryOverview = ref<GalleryOverview | null>(null)
const spacesOverview = ref<SpacesOverview | null>(null)
const category = ref<CategoryStat[]>([])
const tags = ref<TagStat[]>([])
const trend = ref<TrendPoint[]>([])
const storageTrend = ref<StorageTrendPoint[]>([])
const ranking = ref<SpaceRankItem[]>([])

const granularity = ref<Granularity>('day')
const rankingSort = ref<'count' | 'size'>('count')

async function loadAll() {
  loading.value = true
  try {
    const [overview, spaces, cat, tagList, trendList, storageList, rankingList] = await Promise.all([
      analyticsApi.galleryOverview(),
      analyticsApi.spacesOverview(),
      analyticsApi.galleryCategory(),
      analyticsApi.galleryTags(20),
      analyticsApi.galleryTrend(granularity.value),
      analyticsApi.galleryStorageTrend(granularity.value),
      analyticsApi.spacesRanking(10, rankingSort.value),
    ])
    galleryOverview.value = overview
    spacesOverview.value = spaces
    category.value = cat
    tags.value = tagList
    trend.value = trendList
    storageTrend.value = storageList
    ranking.value = rankingList
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

onMounted(loadAll)
</script>

<template>
  <div class="dashboard-container" v-loading="loading">
    <h2 class="page-title">分析仪表盘</h2>

    <!-- 顶部统计卡片 -->
    <div class="stat-grid">
      <el-card class="stat-card" shadow="never">
        <div class="stat-label">图片总数</div>
        <div class="stat-value">{{ galleryOverview?.total_pictures ?? 0 }}</div>
      </el-card>
      <el-card class="stat-card" shadow="never">
        <div class="stat-label">总容量</div>
        <div class="stat-value">{{ formatBytes(galleryOverview?.total_size) }}</div>
      </el-card>
      <el-card class="stat-card" shadow="never">
        <div class="stat-label">总下载量</div>
        <div class="stat-value">{{ galleryOverview?.total_downloads ?? 0 }}</div>
      </el-card>
      <el-card class="stat-card" shadow="never">
        <div class="stat-label">空间总数</div>
        <div class="stat-value">{{ spacesOverview?.total_spaces ?? 0 }}</div>
      </el-card>
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  border-radius: 10px;
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  color: #1f2937;
}

.chart-card {
  border-radius: 10px;
  margin-bottom: 20px;
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
}
</style>
