<script setup lang="ts">
/**
 * 创建团队空间：仅名称（创建者自动成为管理员）
 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({ name: '' })

const rules: FormRules = {
  name: [
    { required: true, message: '请输入团队名称', trigger: 'blur' },
    { min: 1, max: 128, message: '名称长度 1~128 个字符', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    await teamSpaceApi.create({ name: form.name })
    ElMessage.success('团队空间创建成功')
    router.push('/spaces/team')
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '创建失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <el-card class="form-card" shadow="never">
      <template #header>
        <div><div class="eyebrow">COLLABORATION · 新建团队</div><span class="card-title">创建团队空间</span><p class="page-subtitle">邀请伙伴一起整理素材并协作创作</p></div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="团队名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入团队名称" maxlength="128" show-word-limit />
        </el-form-item>
      </el-form>
      <div class="actions">
        <el-button @click="router.push('/spaces/team')">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">创建</el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.form-card {
  max-width: 520px;
  margin: 0 auto;
  border-radius: 10px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
