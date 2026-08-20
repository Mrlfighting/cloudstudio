<script setup lang="ts">
/**
 * 空间图片上传弹窗：文件 + 元信息（FormData 提交，tags 序列化为 JSON 字符串）
 */
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { spaceApi } from '@/api/space'
import { getErrorMessage } from '@/api/http'
import { PICTURE_CATEGORIES } from '@/types/picture'

const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{
  success: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const file = ref<File | null>(null)
const fileList = ref<UploadFile[]>([])

const form = reactive({
  name: '',
  introduction: '',
  category: '',
  tags: [] as string[],
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入图片名称', trigger: 'blur' },
    { max: 128, message: '名称最长 128 个字符', trigger: 'blur' },
  ],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  introduction: [{ max: 512, message: '简介最长 512 个字符', trigger: 'blur' }],
}

function onFileChange(uploadFile: UploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  const okType = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(raw.type)
  if (!okType) {
    ElMessage.error('仅支持 JPEG/PNG/WebP/GIF 格式')
    fileList.value = []
    file.value = null
    return
  }
  if (raw.size > 10 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 10MB')
    fileList.value = []
    file.value = null
    return
  }
  file.value = raw
}

function onFileRemove() {
  file.value = null
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  if (!file.value) {
    ElMessage.warning('请先选择图片文件')
    return
  }

  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('name', form.name)
  if (form.introduction) fd.append('introduction', form.introduction)
  fd.append('category', form.category)
  // 上传接口的 tags 是 JSON 数组字符串（与编辑接口的数组不同）
  fd.append('tags', JSON.stringify(form.tags))

  submitting.value = true
  try {
    await spaceApi.uploadPicture(fd)
    ElMessage.success('上传成功')
    emit('success')
    resetForm()
    visible.value = false
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '上传失败'))
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  form.name = ''
  form.introduction = ''
  form.category = ''
  form.tags = []
  file.value = null
  fileList.value = []
}
</script>

<template>
  <el-dialog v-model="visible" title="上传图片到空间" width="560px" @closed="resetForm">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="图片文件" required>
        <el-upload
          v-model:file-list="fileList"
          drag
          :auto-upload="false"
          :limit="1"
          accept="image/jpeg,image/png,image/webp,image/gif"
          :on-change="onFileChange"
          :on-remove="onFileRemove"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽图片到此处，或<em>点击选择</em></div>
          <template #tip>
            <div class="el-upload__tip">JPEG/PNG/WebP/GIF，不超过 10MB</div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入图片名称" maxlength="128" show-word-limit />
      </el-form-item>

      <el-form-item label="分类" prop="category">
        <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%">
          <el-option v-for="c in PICTURE_CATEGORIES" :key="c" :label="c" :value="c" />
        </el-select>
      </el-form-item>

      <el-form-item label="简介" prop="introduction">
        <el-input
          v-model="form.introduction"
          type="textarea"
          :rows="2"
          maxlength="512"
          show-word-limit
          placeholder="图片简介（可选）"
        />
      </el-form-item>

      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入标签后回车添加（可选）"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">上传</el-button>
    </template>
  </el-dialog>
</template>
