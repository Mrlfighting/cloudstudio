<script setup lang="ts">
/**
 * 空间详情弹窗：基本信息 + 容量/数量进度
 */
import { computed } from 'vue'
import { formatBytes, spaceLevelLabel, type SpaceListItemRead } from '@/types/space'

const visible = defineModel<boolean>({ default: false })
const props = defineProps<{
  space: SpaceListItemRead | null
}>()

const capacityPercent = computed(() => {
  if (!props.space || props.space.max_size <= 0) return 0
  return Math.min(100, Math.round((props.space.total_size / props.space.max_size) * 100))
})

const countPercent = computed(() => {
  if (!props.space || props.space.max_count <= 0) return 0
  return Math.min(100, Math.round((props.space.total_count / props.space.max_count) * 100))
})
</script>

<template>
  <el-dialog v-model="visible" title="空间详情" width="520px">
    <template v-if="space">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="名称">{{ space.name }}</el-descriptions-item>
        <el-descriptions-item label="级别">
          <el-tag size="small" type="info">{{ spaceLevelLabel(space.space_level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="所属用户 ID">{{ space.user_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="space.status === 'active' ? 'success' : 'danger'" size="small">
            {{ space.status === 'active' ? '正常' : '已封禁' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ space.created_at ?? '—' }}</el-descriptions-item>
      </el-descriptions>

      <div class="quota">
        <div class="quota-label">容量使用</div>
        <el-progress
          :percentage="capacityPercent"
          :status="space.total_size > space.max_size ? 'exception' : undefined"
        />
        <div class="quota-text">{{ formatBytes(space.total_size) }} / {{ formatBytes(space.max_size) }}</div>

        <div class="quota-label">图片数量</div>
        <el-progress
          :percentage="countPercent"
          :status="space.total_count > space.max_count ? 'exception' : undefined"
        />
        <div class="quota-text">{{ space.total_count }} / {{ space.max_count }} 张</div>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.quota {
  margin-top: 16px;
}

.quota-label {
  font-weight: 600;
  margin: 12px 0 6px;
}

.quota-text {
  margin-top: 4px;
  font-size: 13px;
  color: #606266;
}
</style>
