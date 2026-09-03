<script setup lang="ts">
/**
 * AI 扩图编辑器弹窗：填参数 → 提交任务 → 轮询结果 → 原图/结果对比 + 下载/重新编辑
 * 可复用：详情页操作栏、卡片悬停菜单均可挂载本组件。
 */
import { onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import type { OutpaintOutputRatio, OutpaintingParameters } from '@/types/outpaint'

const props = defineProps<{
  pictureId: number
  url: string // 原图 URL（用于编辑态预览与结果对比）
}>()

const visible = defineModel<boolean>({ default: false })

type Stage = 'edit' | 'processing' | 'done' | 'error'
const stage = ref<Stage>('edit')
const resultUrl = ref('')
const errorMsg = ref('')
let timer: ReturnType<typeof setInterval> | null = null

const RATIO_OPTIONS: { label: string; value: OutpaintOutputRatio }[] = [
  { label: '保持原图比例', value: '' },
  { label: '1:1', value: '1:1' },
  { label: '3:4', value: '3:4' },
  { label: '4:3', value: '4:3' },
  { label: '9:16', value: '9:16' },
  { label: '16:9', value: '16:9' },
]

const form = reactive({
  output_ratio: '' as OutpaintOutputRatio,
  x_scale: 1,
  y_scale: 1,
  angle: 0,
  top_offset: 0,
  bottom_offset: 0,
  left_offset: 0,
  right_offset: 0,
  best_quality: false,
  limit_image_size: true,
  add_watermark: true,
})

/** 只发送用户实际设置的有效字段（过滤默认值），避免把默认值误传给后端 */
function buildPayload(): OutpaintingParameters {
  const payload: OutpaintingParameters = {}
  if (form.output_ratio) payload.output_ratio = form.output_ratio
  if (form.x_scale !== 1) payload.x_scale = form.x_scale
  if (form.y_scale !== 1) payload.y_scale = form.y_scale
  if (form.angle !== 0) payload.angle = form.angle
  if (form.top_offset) payload.top_offset = form.top_offset
  if (form.bottom_offset) payload.bottom_offset = form.bottom_offset
  if (form.left_offset) payload.left_offset = form.left_offset
  if (form.right_offset) payload.right_offset = form.right_offset
  if (form.best_quality) payload.best_quality = true
  if (!form.limit_image_size) payload.limit_image_size = false
  if (!form.add_watermark) payload.add_watermark = false
  return payload
}

async function submit() {
  if (!props.pictureId) return
  if (Object.keys(buildPayload()).length === 0) {
    ElMessage.warning('请至少设置一项扩图参数（宽高比 / 比例 / 方向填充 / 旋转）')
    return
  }
  stage.value = 'processing'
  errorMsg.value = ''
  resultUrl.value = ''
  try {
    const res = await spaceApi.createOutpaintTask(props.pictureId, buildPayload())
    startPolling(res.task_id)
  } catch (err) {
    stage.value = 'edit'
    ElMessage.error(getErrorMessage(err, '提交扩图任务失败'))
  }
}

function startPolling(taskId: string) {
  stopPolling()
  timer = setInterval(async () => {
    try {
      const res = await spaceApi.queryOutpaintTask(taskId)
      if (res.task_status === 'SUCCEEDED') {
        resultUrl.value = res.output_image_url ?? ''
        stopPolling()
        stage.value = resultUrl.value ? 'done' : 'error'
        if (!resultUrl.value) errorMsg.value = '扩图成功但未返回结果图'
      } else if (res.task_status === 'FAILED' || res.task_status === 'CANCELED') {
        errorMsg.value = res.message ?? res.code ?? '扩图失败'
        stopPolling()
        stage.value = 'error'
      }
    } catch (err) {
      // 轮询偶发网络失败不中断，继续下一轮
      ElMessage.error(getErrorMessage(err, '查询扩图任务失败'))
    }
  }, 2000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function download() {
  if (resultUrl.value) window.open(resultUrl.value, '_blank', 'noopener')
}

function reEdit() {
  stopPolling()
  stage.value = 'edit'
  resultUrl.value = ''
  errorMsg.value = ''
}

function reset() {
  stopPolling()
  stage.value = 'edit'
  resultUrl.value = ''
  errorMsg.value = ''
}

watch(visible, (v) => {
  if (v) reset()
  else stopPolling()
})

onUnmounted(stopPolling)
</script>

<template>
  <el-dialog v-model="visible" title="AI 扩图" width="820px" append-to-body>
    <!-- 编辑态：参数表单 -->
    <template v-if="stage === 'edit'">
      <div class="origin-preview">
        <span class="origin-label">原图</span>
        <el-image
          class="origin-img"
          :src="url"
          fit="contain"
          :preview-src-list="[url]"
          preview-teleported
        />
      </div>

      <el-form label-width="96px" label-position="left">
        <el-form-item label="宽高比">
          <el-select v-model="form.output_ratio" placeholder="保持原图比例" style="width: 100%">
            <el-option v-for="o in RATIO_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="水平扩展">
          <el-slider v-model="form.x_scale" :min="1" :max="3" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="垂直扩展">
          <el-slider v-model="form.y_scale" :min="1" :max="3" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="旋转角度">
          <el-slider v-model="form.angle" :min="0" :max="359" :step="1" show-input />
        </el-form-item>
        <el-form-item label="方向填充">
          <div class="offset-row">
            <span class="offset-item">上<el-input-number v-model="form.top_offset" :min="0" :controls="false" /></span>
            <span class="offset-item">下<el-input-number v-model="form.bottom_offset" :min="0" :controls="false" /></span>
            <span class="offset-item">左<el-input-number v-model="form.left_offset" :min="0" :controls="false" /></span>
            <span class="offset-item">右<el-input-number v-model="form.right_offset" :min="0" :controls="false" /></span>
          </div>
        </el-form-item>
        <el-form-item label="最佳质量">
          <el-switch v-model="form.best_quality" />
          <span class="hint">耗时会成倍增加</span>
        </el-form-item>
        <el-form-item label="限制大小">
          <el-switch v-model="form.limit_image_size" />
        </el-form-item>
        <el-form-item label="AI 水印">
          <el-switch v-model="form.add_watermark" />
        </el-form-item>
      </el-form>

      <el-alert
        type="info"
        :closable="false"
        title="优先级：宽高比 > 比例 > 方向填充；旋转会先执行再扩展。"
      />
    </template>

    <!-- 处理态：轮询中 -->
    <template v-else-if="stage === 'processing'">
      <div class="processing">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p>AI 正在扩图，请稍候…（通常需要几秒到几十秒）</p>
      </div>
    </template>

    <!-- 成功态：原图 / 结果对比 -->
    <template v-else-if="stage === 'done'">
      <div class="compare">
        <div class="compare-item">
          <div class="compare-label">原图</div>
          <el-image :src="url" fit="contain" :preview-src-list="[url]" preview-teleported />
        </div>
        <div class="compare-item">
          <div class="compare-label">扩图结果</div>
          <el-image
            :src="resultUrl"
            fit="contain"
            :preview-src-list="[resultUrl]"
            preview-teleported
          />
        </div>
      </div>
      <p class="result-tip">结果图为阿里云临时地址（24 小时内有效），请及时下载保存。</p>
    </template>

    <!-- 失败态 -->
    <template v-else-if="stage === 'error'">
      <el-result icon="error" title="扩图失败" :sub-title="errorMsg || '请稍后重试'">
        <template #extra>
          <el-button type="primary" @click="reEdit">重新编辑</el-button>
        </template>
      </el-result>
    </template>

    <template #footer>
      <template v-if="stage === 'edit'">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :icon="'MagicStick'" @click="submit">开始扩图</el-button>
      </template>
      <template v-else-if="stage === 'processing'">
        <el-button @click="reEdit">取消</el-button>
      </template>
      <template v-else-if="stage === 'done'">
        <el-button @click="reEdit">重新编辑</el-button>
        <el-button type="primary" :icon="'Download'" @click="download">下载</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<style scoped>
.origin-preview {
  position: relative;
  margin-bottom: 16px;
  background: #f7f8fb;
  border-radius: var(--app-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  max-height: 180px;
  overflow: hidden;
}

.origin-label {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 12px;
  color: #fff;
  background: rgba(0, 0, 0, 0.45);
  padding: 2px 8px;
  border-radius: 4px;
}

.origin-img {
  max-height: 180px;
  width: 100%;
}

.offset-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.offset-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--app-text);
}

.offset-item :deep(.el-input-number) {
  width: 110px;
}

.hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--app-muted);
}

.processing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 0;
  color: #606266;
}

.compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.compare-item {
  background: #f7f8fb;
  border-radius: var(--app-radius-md);
  padding: 8px;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.compare-label {
  align-self: flex-start;
  font-size: 13px;
  color: var(--app-text);
  margin-bottom: 8px;
}

.compare-item :deep(.el-image) {
  flex: 1;
  width: 100%;
  min-height: 240px;
}

.result-tip {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--app-muted);
  text-align: center;
}
</style>
