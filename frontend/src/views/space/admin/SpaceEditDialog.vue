<script setup lang="ts">
/**
 * 空间编辑弹窗：名称 / 级别
 */
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import { SPACE_LEVEL_OPTIONS, type SpaceLevel, type SpaceListItemRead } from '@/types/space'

const visible = defineModel<boolean>({ default: false })
const props = defineProps<{
  space: SpaceListItemRead | null
}>()
const emit = defineEmits<{
  success: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({
  name: '',
  space_level: 0 as SpaceLevel,
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入空间名称', trigger: 'blur' },
    { max: 128, message: '名称最长 128 个字符', trigger: 'blur' },
  ],
}

watch(visible, (v) => {
  if (!v || !props.space) return
  form.name = props.space.name
  form.space_level = props.space.space_level
})

async function handleSubmit() {
  if (!formRef.value || !props.space) return
  await formRef.value.validate()
  submitting.value = true
  try {
    await spaceApi.update(props.space.id, { name: form.name, space_level: form.space_level })
    ElMessage.success('空间信息修改成功')
    emit('success')
    visible.value = false
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '修改失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="编辑空间" width="480px" class="space-edit-dialog">
    <div class="dialog-intro">
      <div class="dialog-icon"><el-icon><Edit /></el-icon></div>
      <div>
        <div class="dialog-kicker">SPACE SETTINGS</div>
        <div class="dialog-heading">更新空间信息</div>
        <div class="dialog-subtitle">调整展示名称与空间等级</div>
      </div>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="空间名称" prop="name">
        <el-input v-model="form.name" maxlength="128" show-word-limit />
      </el-form-item>
      <el-form-item label="空间级别" prop="space_level">
        <el-select v-model="form.space_level" style="width: 100%">
          <el-option
            v-for="o in SPACE_LEVEL_OPTIONS"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-intro { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
.dialog-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 14px; color: #fff; background: linear-gradient(135deg, var(--app-lavender), var(--app-primary)); box-shadow: 8px 8px 0 rgba(220,212,247,.26); }
.dialog-kicker { color: #b16880; font-size: 10px; font-weight: 800; letter-spacing: 1.8px; }
.dialog-heading { margin-top: 3px; font-size: 20px; font-weight: 800; color: var(--app-ink); }
.dialog-subtitle { margin-top: 4px; color: var(--app-muted); font-size: 12px; }
</style>
