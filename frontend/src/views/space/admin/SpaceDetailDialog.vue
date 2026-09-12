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
  <el-dialog v-model="visible" title="空间详情" width="520px" class="space-detail-dialog">
    <template v-if="space">
      <div class="dialog-intro">
        <div class="dialog-icon"><el-icon><FolderOpened /></el-icon></div>
        <div>
          <div class="dialog-kicker">SPACE OVERVIEW</div>
          <div class="dialog-heading">{{ space.name }}</div>
          <div class="dialog-subtitle">查看空间等级、状态与配额使用情况</div>
        </div>
      </div>
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
  margin-top: 20px;
  padding: 16px 18px;
  border: 1px solid var(--app-line-soft);
  border-radius: var(--app-radius-md);
  background: linear-gradient(135deg, #fbfdff, #fff7fa);
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

.dialog-intro { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
.dialog-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 14px; color: #fff; background: linear-gradient(135deg, var(--app-blue), var(--app-primary)); box-shadow: 8px 8px 0 rgba(236,114,150,.12); }
.dialog-kicker { color: #b16880; font-size: 10px; font-weight: 800; letter-spacing: 1.8px; }
.dialog-heading { margin-top: 3px; font-size: 20px; font-weight: 800; color: var(--app-ink); }
.dialog-subtitle { margin-top: 4px; color: var(--app-muted); font-size: 12px; }
</style>
