<script setup lang="ts">
/**
 * 邀请成员弹窗：输入用户 ID + 选择角色
 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { teamSpaceApi } from '@/api/teamSpace'
import { userApi } from '@/api/user'
import { getErrorMessage } from '@/api/http'
import { SPACE_ROLE_OPTIONS, type SpaceRole } from '@/types/teamSpace'
import type { UserSearchItem } from '@/types/user'

const visible = defineModel<boolean>({ default: false })
const props = defineProps<{
  spaceId: number
}>()
const emit = defineEmits<{
  success: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const userOptions = ref<UserSearchItem[]>([])
const searchLoading = ref(false)

const form = reactive({
  user_id: null as number | null,
  space_role: 'viewer' as SpaceRole,
})

const rules: FormRules = {
  user_id: [{ required: true, message: '请选择用户', trigger: 'change' }],
  space_role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

async function searchUsers(keyword: string) {
  if (!keyword) {
    userOptions.value = []
    return
  }
  searchLoading.value = true
  try {
    userOptions.value = await userApi.searchUsers(keyword)
  } catch {
    userOptions.value = []
  } finally {
    searchLoading.value = false
  }
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
        <div class="dialog-subtitle">搜索用户并设置初始协作权限</div>
      </div>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="用户" prop="user_id">
        <el-select
          v-model="form.user_id"
          filterable
          remote
          reserve-keyword
          :remote-method="searchUsers"
          :loading="searchLoading"
          placeholder="输入用户名或昵称搜索"
          style="width: 100%"
        >
          <el-option
            v-for="u in userOptions"
            :key="u.id"
            :label="`${u.name}（@${u.username}）`"
            :value="u.id"
          />
        </el-select>
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
