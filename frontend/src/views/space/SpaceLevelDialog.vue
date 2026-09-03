<script setup lang="ts">
/**
 * 空间级别变更弹窗：升级/降级
 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import { SPACE_LEVEL_OPTIONS, spaceLevelLabel, type SpaceLevel } from '@/types/space'

const visible = defineModel<boolean>({ default: false })
const props = defineProps<{
  currentLevel: SpaceLevel
}>()
const emit = defineEmits<{
  success: []
}>()

const submitting = ref(false)
const target = ref<SpaceLevel>(0)

watch(visible, (v) => {
  if (v) target.value = props.currentLevel
})

const isUpgrade = computed(() => target.value > props.currentLevel)

async function handleSubmit() {
  if (target.value === props.currentLevel) {
    ElMessage.warning('请选择要变更到的级别')
    return
  }
  submitting.value = true
  try {
    await spaceApi.changeLevel(target.value)
    ElMessage.success(isUpgrade.value ? '空间已升级' : '空间已降级')
    emit('success')
    visible.value = false
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '变更级别失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="变更空间级别" width="480px">
    <div class="level-tip">
      当前级别：<el-tag size="small" type="info">{{ spaceLevelLabel(props.currentLevel) }}</el-tag>
    </div>

    <el-form label-position="top">
      <el-form-item label="目标级别">
        <el-select v-model="target" style="width: 100%">
          <el-option
            v-for="o in SPACE_LEVEL_OPTIONS"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="isUpgrade"
      type="info"
      :closable="false"
      show-icon
      title="升级说明"
      description="升级后配额立即生效。"
    />
    <el-alert
      v-else
      type="warning"
      :closable="false"
      show-icon
      title="降级提示"
      description="若当前用量超过目标级别上限，降级将被拒绝。"
    />

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确认变更</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.level-tip {
  margin-bottom: 12px;
  color: var(--app-text);
}
</style>
