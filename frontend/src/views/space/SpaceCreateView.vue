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

/** 私有空间三级配额（对齐后端 space/constants.py） */
const levels = [
  { name: '普通版', size: '500MB', count: '100' },
  { name: '专业版', size: '5GB', count: '1000' },
  { name: '旗舰版', size: '10GB', count: '3000' },
]

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
    <div class="page-intro"><div class="eyebrow">PRIVATE SPACE · 新建空间</div><h2 class="page-title">创建空间</h2><p class="page-subtitle">建立一个只属于你的灵感收纳地</p></div>

    <div class="create-layout">
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

      <aside class="benefits-panel">
        <h3>空间权益</h3>
        <p class="benefits-note">创建后默认「普通版」，可随时在空间内升级 / 降级。</p>
        <div class="level-list">
          <div v-for="l in levels" :key="l.name" class="level-item">
            <div class="level-name">{{ l.name }}</div>
            <div class="level-meta">{{ l.size }} · {{ l.count }} 张图片</div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.create-layout {
  display: grid;
  grid-template-columns: minmax(320px, 440px) minmax(300px, 1fr);
  gap: 20px;
  align-items: start;
}

.create-card {
  border-radius: var(--app-radius-lg);
}

.benefits-panel {
  padding: 24px 26px;
  border: 1px solid var(--app-line);
  border-radius: var(--app-radius-lg);
  background: var(--app-surface);
  box-shadow: var(--app-shadow-soft);
}

.benefits-panel h3 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 800;
  color: var(--app-ink);
}

.benefits-note {
  margin: 0 0 18px;
  color: var(--app-muted);
  font-size: 13px;
  line-height: 1.7;
}

.level-list {
  display: grid;
  gap: 12px;
}

.level-item {
  padding: 14px 16px;
  border-radius: var(--app-radius-md);
  background: #f8fafc;
  border: 1px solid var(--app-line-soft);
}

.level-name {
  font-size: 15px;
  font-weight: 800;
  color: var(--app-ink);
}

.level-meta {
  margin-top: 6px;
  color: var(--app-muted);
  font-size: 13px;
}

@media (max-width: 760px) {
  .create-layout {
    grid-template-columns: 1fr;
  }
}
</style>
