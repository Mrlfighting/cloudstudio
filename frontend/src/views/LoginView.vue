<script setup lang="ts">
/**
 * 登录页：账号 + 密码
 */
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  account: '',
  password: '',
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
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.login(form.account, form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/profile'
    router.replace(redirect)
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '登录失败'))
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
        <div class="auth-heading">欢迎回来</div>
        <div class="auth-kicker">登录云上工坊，继续发现灵感</div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item label="账号" prop="account">
          <el-input
            v-model="form.account"
            placeholder="请输入账号"
            :prefix-icon="'User'"
            clearable
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
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="submit-btn" :loading="loading" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="switch-link">
        还没有账号？<router-link to="/register">去注册</router-link>
      </div>
    </el-card>

    <SiteFooter fixed />
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
