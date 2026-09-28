<script setup lang="ts">
/** 注册表单：注册不会建立会话，成功后由父组件切回登录。 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api/auth'
import { getErrorMessage } from '@/api/http'

const emit = defineEmits<{
  success: [account: string]
  switchLogin: []
}>()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  account: '',
  password: '',
  confirm_password: '',
  nickname: '',
  user_profile: '',
})

const rules: FormRules = {
  account: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { pattern: /^[a-z0-9]{2,20}$/, message: '账号为 2-20 位小写字母或数字', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
  nickname: [{ max: 30, message: '昵称最长 30 个字符', trigger: 'blur' }],
  user_profile: [{ max: 512, message: '简介最长 512 个字符', trigger: 'blur' }],
}

async function handleRegister(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authApi.register({
      account: form.account,
      password: form.password,
      confirm_password: form.confirm_password,
      ...(form.nickname ? { nickname: form.nickname } : {}),
      ...(form.user_profile ? { user_profile: form.user_profile } : {}),
    })
    const account = form.account
    form.password = ''
    form.confirm_password = ''
    ElMessage.success('注册成功，请登录')
    emit('success', account)
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '注册失败'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleRegister">
    <el-form-item label="账号" prop="account">
      <el-input v-model="form.account" placeholder="2-20 位小写字母或数字" :prefix-icon="'User'" clearable autocomplete="username" />
    </el-form-item>
    <el-form-item label="密码" prop="password">
      <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" :prefix-icon="'Lock'" autocomplete="new-password" />
    </el-form-item>
    <el-form-item label="确认密码" prop="confirm_password">
      <el-input v-model="form.confirm_password" type="password" show-password placeholder="请再次输入密码" :prefix-icon="'CircleCheck'" autocomplete="new-password" />
    </el-form-item>
    <el-form-item label="昵称（可选）" prop="nickname">
      <el-input v-model="form.nickname" placeholder="请输入昵称" :prefix-icon="'MagicStick'" clearable />
    </el-form-item>
    <el-form-item label="简介（可选）" prop="user_profile">
      <el-input
        v-model="form.user_profile"
        type="textarea"
        :rows="2"
        maxlength="512"
        show-word-limit
        placeholder="介绍一下自己吧"
      />
    </el-form-item>
    <el-form-item>
      <el-button native-type="submit" type="primary" class="auth-submit" :loading="loading">注册</el-button>
    </el-form-item>
  </el-form>
  <div class="auth-switch">
    已有账号？<el-button link type="primary" @click="emit('switchLogin')">去登录</el-button>
  </div>
</template>

<style scoped>
.auth-submit { width: 100%; height: 44px; }
.auth-switch { text-align: center; font-size: 13px; color: var(--app-muted); }
.auth-switch :deep(.el-button) { padding: 0; color: #b4677e; font-weight: 700; }
</style>
