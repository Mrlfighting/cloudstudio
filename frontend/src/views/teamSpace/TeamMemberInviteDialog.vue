<script setup lang="ts">
/**
 * 邀请成员弹窗：输入用户 ID + 选择角色
 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { SPACE_ROLE_OPTIONS, type SpaceRole } from '@/types/teamSpace'

const visible = defineModel<boolean>({ default: false })
const props = defineProps<{
  spaceId: number
}>()
const emit = defineEmits<{
  success: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  user_id: null as number | null,
  space_role: 'viewer' as SpaceRole,
})

const rules: FormRules = {
  user_id: [{ required: true, message: '请输入用户 ID', trigger: 'blur' }],
  space_role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    await teamSpaceApi.addMember(props.spaceId, {
      user_id: form.user_id!,
      space_role: form.space_role,
    })
    ElMessage.success('成员已加入')
    emit('success')
    form.user_id = null
    form.space_role = 'viewer'
    visible.value = false
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '邀请成员失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="邀请成员" width="420px" class="invite-dialog">
    <div class="dialog-intro">
      <div class="dialog-icon"><el-icon><UserFilled /></el-icon></div>
      <div>
        <div class="dialog-kicker">TEAM MEMBERS</div>
        <div class="dialog-heading">邀请协作者加入</div>
        <div class="dialog-subtitle">输入用户 ID 并设置初始协作权限</div>
      </div>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="用户 ID" prop="user_id">
        <el-input-number v-model="form.user_id" :min="1" :controls="false" placeholder="输入用户 ID" style="width: 100%" />
      </el-form-item>
      <el-form-item label="角色" prop="space_role">
        <el-select v-model="form.space_role" style="width: 100%">
          <el-option v-for="o in SPACE_ROLE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">邀请</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-intro { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
.dialog-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 14px; color: #fff; background: linear-gradient(135deg, var(--app-mint), var(--app-blue)); box-shadow: 8px 8px 0 rgba(159,220,244,.24); }
.dialog-kicker { color: #5b8a87; font-size: 10px; font-weight: 800; letter-spacing: 1.8px; }
.dialog-heading { margin-top: 3px; font-size: 20px; font-weight: 800; color: var(--app-ink); }
.dialog-subtitle { margin-top: 4px; color: var(--app-muted); font-size: 12px; }
</style>
