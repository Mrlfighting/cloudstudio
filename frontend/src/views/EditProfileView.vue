<script setup lang="ts">
/**
 * 编辑资料：昵称/用户名/邮箱/头像/简介
 * 注意：PATCH 路径使用【编辑前的 username】；成功后重新 GET /me 刷新 store
 */
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { userApi } from '@/api/user'
import { getErrorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { UpdateProfilePayload } from '@/types/user'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  name: '',
  username: '',
  email: '',
  profile_image_url: '',
  user_profile: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 2, max: 30, message: '昵称长度为 2-30 个字符', trigger: 'blur' },
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-z0-9]{2,20}$/, message: '用户名为 2-20 位小写字母或数字', trigger: 'blur' },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  profile_image_url: [
    {
      pattern: /^(https?|ftp):\/\/[^\s/$.?#][^\s]*$/,
      message: '请输入合法的图片地址（http/https/ftp）',
      trigger: 'blur',
    },
  ],
  user_profile: [{ max: 512, message: '简介最长 512 个字符', trigger: 'blur' }],
}

function prefill() {
  if (!auth.user) return
  form.name = auth.user.name
  form.username = auth.user.username
  form.email = auth.user.email ?? ''
  form.profile_image_url = auth.user.profile_image_url ?? ''
  form.user_profile = auth.user.user_profile ?? ''
}

async function load() {
  if (!auth.user) {
    const me = await userApi.getMe()
    auth.setUser(me)
  }
  prefill()
}

load()

async function handleSubmit() {
  if (!formRef.value || !auth.user) return
  await formRef.value.validate()

  // 空的可选字段发送 null（清空邮箱/头像/简介）；昵称与用户名始终提交
  const payload: UpdateProfilePayload = {
    name: form.name,
    username: form.username,
    email: form.email.trim() ? form.email.trim() : null,
    profile_image_url: form.profile_image_url.trim() ? form.profile_image_url.trim() : null,
    user_profile: form.user_profile.trim() ? form.user_profile.trim() : null,
  }

  // PATCH 用编辑前的 username（后端按路径校验权限并定位用户）
  const oldUsername = auth.user.username

  loading.value = true
  try {
    await userApi.updateProfile(oldUsername, payload)
    ElMessage.success('资料更新成功')
    const me = await userApi.getMe()
    auth.setUser(me)
    router.push('/profile')
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '资料更新失败，该用户名或邮箱可能已被占用'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-intro"><div class="eyebrow">ACCOUNT · 账号设置</div><h2 class="page-title">编辑资料</h2><p class="page-subtitle">更新你的公开资料和头像信息</p></div>

    <el-card class="edit-card">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="昵称" prop="name">
          <el-input v-model="form.name" placeholder="请输入昵称" maxlength="30" show-word-limit />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="2-20 位小写字母或数字"
            maxlength="20"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" clearable />
        </el-form-item>
        <el-form-item label="头像地址" prop="profile_image_url">
          <el-input v-model="form.profile_image_url" placeholder="https://..." clearable />
        </el-form-item>
        <el-form-item label="简介" prop="user_profile">
          <el-input
            v-model="form.user_profile"
            type="textarea"
            :rows="3"
            maxlength="512"
            show-word-limit
            placeholder="介绍一下自己吧"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
          <el-button @click="router.push('/profile')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.edit-card {
  max-width: 640px;
  border-radius: 10px;
}
</style>
