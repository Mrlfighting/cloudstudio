<script setup lang="ts">
/**
 * 图片上传弹窗（通用）：文件 + 元信息（FormData 提交，tags 序列化为 JSON 字符串）
 * - kind='picture'：公共图库（上传后待审核）
 * - kind='space'：私有空间（直接 approved）
 * - kind='team'：团队空间（直接 approved）
 */
import { computed, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { pictureApi } from '@/api/picture'
import { spaceApi } from '@/api/space'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { PICTURE_CATEGORIES, type PictureKind } from '@/types/picture'
import ImageCropper from '@/components/ImageCropper.vue'

const visible = defineModel<boolean>({ default: false })
const props = withDefaults(
  defineProps<{
    kind?: PictureKind
    spaceId?: number
  }>(),
  { kind: 'picture' },
)
const emit = defineEmits<{
  success: []
}>()

const title = computed(() => {
  if (props.kind === 'space') return '上传图片到空间'
  if (props.kind === 'team') return '上传图片到团队空间'
  return '上传图片'
})

const formRef = ref<FormInstance>()
const submitting = ref(false)
const file = ref<File | null>(null)
const fileList = ref<UploadFile[]>([])
const cropperVisible = ref(false)
const previewUrl = ref('')

function setPreview(f: File | null) {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = f ? URL.createObjectURL(f) : ''
}

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
  setPreview(raw)
}

function onFileRemove() {
  file.value = null
  setPreview(null)
}

function onCropConfirm(blob: Blob) {
  const name = file.value?.name ?? 'image.jpg'
  file.value = new File([blob], name, { type: blob.type || file.value?.type })
  setPreview(file.value)
  cropperVisible.value = false
  ElMessage.success('裁剪完成')
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
    if (props.kind === 'space') {
      await spaceApi.uploadPicture(fd)
      ElMessage.success('上传成功')
    } else if (props.kind === 'team') {
      await teamSpaceApi.uploadPicture(props.spaceId!, fd)
      ElMessage.success('上传成功')
    } else {
      await pictureApi.upload(fd)
      ElMessage.success('上传成功，等待审核')
    }
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
  setPreview(null)
}
</script>

<template>
  <el-dialog v-model="visible" :title="title" width="560px" @closed="resetForm">
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
          <template v-if="!file">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处，或<em>点击选择</em></div>
          </template>
          <img v-else :src="previewUrl" class="preview-img" alt="图片预览" />
          <template #tip>
            <div class="el-upload__tip">JPEG/PNG/WebP/GIF，不超过 10MB</div>
          </template>
        </el-upload>
        <div v-if="file" class="crop-row">
          <el-button :icon="'Crop'" @click="cropperVisible = true">裁剪图片</el-button>
        </div>
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

  <ImageCropper v-if="file" v-model="cropperVisible" :file="file" @confirm="onCropConfirm" />
</template>

<style scoped>
.preview-img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
  display: block;
  margin: 0 auto;
  border-radius: var(--app-radius-md);
}

:deep(.el-upload-dragger) { border: 1px dashed #e7b6c5; border-radius: var(--app-radius-md); background: #fff9fb; transition: .2s; }
:deep(.el-upload-dragger:hover) { border-color: var(--app-primary); background: var(--app-primary-soft); }
:deep(.el-upload__text em) { color: #b85a78; font-style: normal; font-weight: 700; }

.crop-row {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}
</style>
