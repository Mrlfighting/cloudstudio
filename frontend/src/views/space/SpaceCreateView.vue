<script setup lang="ts">
/**
 * 创建私有空间：仅填名称
 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'

const router = useRouter()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ name: '' })

const rules: FormRules = {
  name: [
    { required: true, message: '请输入空间名称', trigger: 'blur' },
    { max: 128, message: '名称最长 128 个字符', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    await spaceApi.create({ name: form.name })
    ElMessage.success('空间创建成功')
    router.push('/spaces/gallery')
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '创建空间失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">创建空间</h2>

    <el-card class="create-card" shadow="never">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="空间名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入空间名称"
            maxlength="128"
            show-word-limit
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">创建</el-button>
          <el-button @click="router.push('/spaces')">返回</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.create-card {
  border-radius: 10px;
  max-width: 480px;
}
</style>
