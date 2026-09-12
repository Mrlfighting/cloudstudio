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

/** 团队空间三角色（对齐后端 RBAC） */
const roles = [
  { name: '管理员', desc: '管理成员、团队设置与所有图片' },
  { name: '编辑者', desc: '上传、编辑与删除图片' },
  { name: '查看者', desc: '浏览团队图片' },
]

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
    <div class="create-layout">
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

      <aside class="benefits-panel">
        <h3>团队协作</h3>
        <p class="benefits-note">创建者自动成为管理员，可邀请成员并分配角色，多人实时协作整理素材。</p>
        <div class="role-list">
          <div v-for="r in roles" :key="r.name" class="role-item">
            <div class="role-name">{{ r.name }}</div>
            <div class="role-desc">{{ r.desc }}</div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.create-layout {
  display: grid;
  grid-template-columns: minmax(340px, 460px) minmax(300px, 1fr);
  gap: 20px;
  align-items: start;
}

.form-card {
  border-radius: var(--app-radius-lg);
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

.role-list {
  display: grid;
  gap: 12px;
}

.role-item {
  padding: 14px 16px;
  border-radius: var(--app-radius-md);
  background: #f8fafc;
  border: 1px solid var(--app-line-soft);
}

.role-name {
  font-size: 15px;
  font-weight: 800;
  color: var(--app-ink);
}

.role-desc {
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
