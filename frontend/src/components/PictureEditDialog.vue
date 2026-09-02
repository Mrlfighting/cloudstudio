<script setup lang="ts">
/**
 * 图片编辑弹窗（通用）：仅编辑元信息（tags 传数组，JSON body）
 * - kind='picture'：公共图库 / 'space'：私有空间 / 'team'：团队空间（需 spaceId）
 */
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { pictureApi } from '@/api/picture'
import { spaceApi } from '@/api/space'
import { teamSpaceApi } from '@/api/teamSpace'
import { getErrorMessage } from '@/api/http'
import { PICTURE_CATEGORIES, type PictureCategory, type PictureKind, type PictureListItemRead } from '@/types/picture'

const visible = defineModel<boolean>({ default: false })
const props = withDefaults(
  defineProps<{
    picture: PictureListItemRead | null
    kind?: PictureKind
    spaceId?: number
  }>(),
  { kind: 'picture' },
)
const emit = defineEmits<{
  success: []
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

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
  introduction: [{ max: 512, message: '简介最长 512 个字符', trigger: 'blur' }],
}

// 打开时加载详情补齐 introduction（列表项不含该字段）
watch(visible, async (v) => {
  if (!v || !props.picture) return
  form.name = props.picture.name
  form.category = props.picture.category ?? ''
  form.tags = [...props.picture.tags]
  form.introduction = ''
  try {
    let detail
    if (props.kind === 'space') detail = await spaceApi.getPicture(props.picture.id)
    else if (props.kind === 'team') detail = await teamSpaceApi.getPicture(props.spaceId!, props.picture.id)
    else detail = await pictureApi.get(props.picture.id)
    form.introduction = detail.introduction ?? ''
  } catch {
    // 详情加载失败时简介留空，不影响编辑其它字段
  }
})

async function handleSubmit() {
  if (!formRef.value || !props.picture) return
  await formRef.value.validate()

  const payload = {
    name: form.name,
    introduction: form.introduction || undefined,
    category: form.category as PictureCategory | undefined,
    tags: form.tags,
  }

  submitting.value = true
  try {
    // 编辑接口的 tags 是数组（JSON body），与上传接口的 JSON 字符串不同
    if (props.kind === 'space') {
      await spaceApi.updatePicture(props.picture.id, payload)
    } else if (props.kind === 'team') {
      await teamSpaceApi.updatePicture(props.spaceId!, props.picture.id, payload)
    } else {
      await pictureApi.update(props.picture.id, payload)
    }
    ElMessage.success('图片信息修改成功')
    emit('success')
    visible.value = false
  } catch (err) {
    ElMessage.error(getErrorMessage(err, '修改失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="编辑图片" width="520px">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" maxlength="128" show-word-limit />
      </el-form-item>
      <el-form-item label="分类" prop="category">
        <el-select v-model="form.category" placeholder="请选择分类" clearable style="width: 100%">
          <el-option v-for="c in PICTURE_CATEGORIES" :key="c" :label="c" :value="c" />
        </el-select>
      </el-form-item>
      <el-form-item label="简介" prop="introduction">
        <el-input
          v-model="form.introduction"
          type="textarea"
          :rows="3"
          maxlength="512"
          show-word-limit
        />
      </el-form-item>
      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入标签后回车添加"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>
