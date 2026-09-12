<script setup lang="ts">
/**
 * 注册页：账号 + 密码 + 确认密码（可选昵称/简介）
 */
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api/auth'
import { getErrorMessage } from '@/api/http'

const router = useRouter()

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

async function handleRegister() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await authApi.register({
      account: form.account,
      password: form.password,
      confirm_password: form.confirm_password,
      ...(form.nickname ? { nickname: form.nickname } : {}),
      ...(form.user_profile ? { user_profile: form.user_profile } : {}),
    })
    ElMessage.success('注册成功，请登录')
    router.push({ path: '/login', query: { account: form.account } })
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '注册失败'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-decoration" aria-hidden="true"><span></span><i></i><b></b></div>
    <el-card class="auth-card">
      <template #header>
        <div class="auth-heading">创建你的空间</div>
        <div class="auth-kicker">加入云上工坊，收藏每一份灵感</div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item label="账号" prop="account">
          <el-input v-model="form.account" placeholder="2-20 位小写字母或数字" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少 8 位"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            show-password
            placeholder="请再次输入密码"
          />
        </el-form-item>
        <el-form-item label="昵称（可选）" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" clearable />
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
          <el-button type="primary" class="submit-btn" :loading="loading" @click="handleRegister">
            注册
          </el-button>
        </el-form-item>
      </el-form>
      <div class="switch-link">
        已有账号？<router-link to="/login">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.submit-btn {
  width: 100%;
}

.switch-link {
  text-align: center;
  font-size: 14px;
  color: #606266;
}

.switch-link a {
  color: #409eff;
  text-decoration: none;
}
</style>
