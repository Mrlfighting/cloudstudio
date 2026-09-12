<script setup lang="ts">
/**
 * 图片协同编辑悬浮工具栏：进入/退出编辑、缩放、旋转、裁剪、保存，以及「谁在编辑」提示。
 */
defineProps<{
  isEditing: boolean
  editorUser: { id: number; name?: string; username?: string } | null
}>()

const emit = defineEmits<{
  enter: []
  exit: []
  'zoom-in': []
  'zoom-out': []
  'rotate-left': []
  'rotate-right': []
  crop: []
  save: []
}>()
</script>

<template>
  <div class="collab-toolbar">
    <div class="status-row">
      <span v-if="editorUser" class="editing-hint">
        <el-icon><Edit /></el-icon>
        {{ editorUser.name || editorUser.username }} 正在编辑
      </span>
      <span v-else-if="isEditing" class="editing-hint self">你正在编辑</span>
      <span v-else class="editing-hint idle">未在编辑</span>
    </div>

    <div class="btn-row">
      <template v-if="isEditing">
        <el-button size="small" :icon="'ZoomOut'" title="缩小" @click="emit('zoom-out')" />
        <el-button size="small" :icon="'ZoomIn'" title="放大" @click="emit('zoom-in')" />
        <el-button size="small" :icon="'RefreshLeft'" title="左旋" @click="emit('rotate-left')" />
        <el-button size="small" :icon="'RefreshRight'" title="右旋" @click="emit('rotate-right')" />
        <el-button size="small" :icon="'Crop'" title="裁剪" @click="emit('crop')" />
        <el-button size="small" type="primary" @click="emit('save')">保存</el-button>
        <el-button size="small" @click="emit('exit')">退出编辑</el-button>
      </template>
      <el-button v-else size="small" type="primary" :icon="'Edit'" @click="emit('enter')">
        进入编辑
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.collab-toolbar {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--app-line);
  border-radius: 999px;
  box-shadow: var(--app-shadow-soft);
  backdrop-filter: blur(14px);
}

.status-row {
  display: flex;
  align-items: center;
}

.editing-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--app-muted);
}

.editing-hint.self {
  color: #b85a78;
}

.editing-hint.idle {
  color: #b5bbc5;
}

.btn-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
