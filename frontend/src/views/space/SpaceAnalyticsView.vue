<script setup lang="ts">
/**
 * 用户「我的空间分析」：个人空间使用情况 + 上传趋势 + 分类/标签分布 + 热门图片
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { EChartsOption } from 'echarts'
import { analyticsApi } from '@/api/analytics'
import { getErrorMessage } from '@/api/http'
import { formatBytes } from '@/types/space'
import type { CategoryStat, Granularity, MySpaceOverview, MyTopPicture, TagStat, TrendPoint } from '@/types/analytics'
import BaseChart from '@/components/BaseChart.vue'
import PageIntro from '@/components/PageIntro.vue'
import StatCard from '@/components/StatCard.vue'

const router = useRouter()

const loading = ref(false)
const trendLoading = ref(false)
const overview = ref<MySpaceOverview | null>(null)
const trend = ref<TrendPoint[]>([])
const category = ref<CategoryStat[]>([])
const tags = ref<TagStat[]>([])
const topPictures = ref<MyTopPicture[]>([])

const granularity = ref<Granularity>('day')

const hasSpace = computed(() => overview.value?.space_id != null)

async function loadAll() {
  loading.value = true
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
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取分析数据失败'))
  } finally {
    loading.value = false
  }
}

async function reloadTrend() {
  trendLoading.value = true
  try {
    trend.value = await analyticsApi.myTrend(granularity.value)
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '获取趋势数据失败'))
  } finally {
    trendLoading.value = false
  }
}

// ---- 进度/百分比 ----

function sizePercent(): number {
  if (!overview.value) return 0
  return Math.min(100, Math.round((overview.value.size_usage ?? 0) * 100))
}

function countPercent(): number {
  if (!overview.value) return 0
  return Math.min(100, Math.round((overview.value.count_usage ?? 0) * 100))
}

// ---- 图表 option ----

const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: trend.value.map((t) => t.period) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'line', smooth: true, data: trend.value.map((t) => t.count) }],
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

const tagsOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 90, right: 30, top: 10, bottom: 30 },
  xAxis: { type: 'value', minInterval: 1 },
  yAxis: { type: 'category', data: tags.value.map((t) => t.tag), inverse: true },
  series: [{ type: 'bar', data: tags.value.map((t) => t.count), barMaxWidth: 20 }],
}))

onMounted(loadAll)
</script>

<template>
  <div class="dashboard-container" v-loading="loading">
    <PageIntro eyebrow="INSIGHTS · 空间分析" title="我的空间分析" subtitle="用数据了解你的存储和创作趋势" />

    <!-- 无空间空态 -->
    <el-result
      v-if="!loading && overview && !hasSpace"
      icon="info"
      title="你还没有创建私有空间"
      sub-title="创建空间后即可查看个人图库分析数据"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/spaces')">前往我的空间</el-button>
      </template>
    </el-result>

    <template v-else-if="overview">
      <!-- 顶部统计卡片 -->
      <div class="stat-grid">
        <StatCard label="图片数量" :value="overview.picture_count" :hint="`/ ${overview.max_count}`" />
        <StatCard label="已用容量" :value="formatBytes(overview.total_size)" :hint="`/ ${formatBytes(overview.max_size)}`" />
        <StatCard label="容量使用率" :value="sizePercent()" hint="%" />
      </div>

      <!-- 容量使用进度 -->
      <el-card class="chart-card" shadow="never">
        <template #header><span>容量使用情况</span></template>
        <div class="quota-grid">
          <div class="quota-item">
            <div class="quota-label">容量使用</div>
            <el-progress :percentage="sizePercent()" :status="sizePercent() >= 100 ? 'exception' : undefined" />
            <div class="quota-text">{{ formatBytes(overview.total_size) }} / {{ formatBytes(overview.max_size) }}</div>
          </div>
          <div class="quota-item">
            <div class="quota-label">图片数量</div>
            <el-progress :percentage="countPercent()" :status="countPercent() >= 100 ? 'exception' : undefined" />
            <div class="quota-text">{{ overview.picture_count }} / {{ overview.max_count }}</div>
          </div>
        </div>
      </el-card>

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
          <el-empty v-else description="暂无上传记录" />
        </div>
      </el-card>

      <!-- 分类 / 标签分布 -->
      <div class="chart-row">
        <el-card class="chart-card" shadow="never">
          <template #header><span>分类分布</span></template>
          <BaseChart v-if="category.length" :option="categoryOption" />
          <el-empty v-else description="暂无分类数据" />
        </el-card>
        <el-card class="chart-card" shadow="never">
          <template #header><span>标签分布</span></template>
          <BaseChart v-if="tags.length" :option="tagsOption" />
          <el-empty v-else description="暂无标签数据" />
        </el-card>
      </div>

      <!-- 热门图片排行 -->
      <el-card class="chart-card" shadow="never">
        <template #header><span>热门图片 TOP 10</span></template>
        <el-empty v-if="!topPictures.length" description="暂无图片" />
        <ul v-else class="hot-list">
          <li v-for="(p, i) in topPictures" :key="p.picture_id" class="hot-item">
            <span class="rank" :class="{ top: i < 3 }">{{ i + 1 }}</span>
            <el-image class="hot-thumb" :src="p.url" fit="cover" :preview-src-list="[p.url]" preview-teleported />
            <span class="hot-name">{{ p.name }}</span>
            <span class="hot-count">
              <el-icon><Download /></el-icon>
              {{ p.download_count }}
            </span>
          </li>
        </ul>
      </el-card>
    </template>
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
  grid-template-columns: repeat(3, 1fr);
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
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
}

.unit {
  font-size: 13px;
  font-weight: 400;
  color: #909399;
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

.quota-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.quota-label {
  font-weight: 600;
  margin-bottom: 8px;
}

.quota-text {
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.hot-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.hot-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f2f5;
}

.hot-item:last-child {
  border-bottom: none;
}

.rank {
  width: 24px;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #909399;
}

.rank.top {
  color: #f56c6c;
}

.hot-thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  flex-shrink: 0;
}

.hot-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #303133;
}

.hot-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #909399;
  font-size: 13px;
}

@media (max-width: 900px) {
  .stat-grid,
  .chart-row,
  .quota-grid {
    grid-template-columns: 1fr;
  }
}
</style>
