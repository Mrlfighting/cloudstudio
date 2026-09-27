<script setup lang="ts">
/** 登录表单：供独立登录页和全局认证弹窗复用。 */
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { UserRead } from '@/types/user'

const props = withDefaults(defineProps<{
  initialAccount?: string
  submitLabel?: string
}>(), {
  initialAccount: '',
  submitLabel: '登录',
})

const emit = defineEmits<{
  success: [user: UserRead]
  switchRegister: []
}>()

const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ account: '', password: '' })

const rules: FormRules = {
  account: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { pattern: /^[a-z0-9]{2,20}$/, message: '账号为 2-20 位小写字母或数字', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
}

watch(
  () => props.initialAccount,
  (account) => {
    if (account) form.account = account
  },
  { immediate: true },
)

async function handleLogin(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const user = await auth.login(form.account, form.password)
    form.password = ''
    ElMessage.success('登录成功')
    emit('success', user)
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '登录失败'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
    <el-form-item label="账号" prop="account">
      <el-input
        v-model="form.account"
        placeholder="请输入账号"
        :prefix-icon="'User'"
        clearable
        autocomplete="username"
        @keyup.enter="handleLogin"
      />
    </el-form-item>
    <el-form-item label="密码" prop="password">
      <el-input
        v-model="form.password"
        type="password"
        show-password
        placeholder="请输入密码"
        :prefix-icon="'Lock'"
        autocomplete="current-password"
        @keyup.enter="handleLogin"
      />
    </el-form-item>
    <el-form-item>
      <el-button native-type="submit" type="primary" class="auth-submit" :loading="loading">
        {{ submitLabel }}
      </el-button>
    </el-form-item>
  </el-form>
  <div class="auth-switch">
    还没有账号？<el-button link type="primary" @click="emit('switchRegister')">去注册</el-button>
  </div>
</template>

<style scoped>
.auth-submit { width: 100%; height: 44px; }
.auth-switch { text-align: center; font-size: 13px; color: var(--app-muted); }
.auth-switch :deep(.el-button) { padding: 0; color: #b4677e; font-weight: 700; }
</style>
