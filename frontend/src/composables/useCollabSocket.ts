/**
 * 图片协同编辑 WebSocket 客户端。
 * 建立与后端的 WS 连接，维护当前视图状态、谁在编辑、是否持有编辑锁。
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { CropRect, PictureEditState } from '@/types/picture'

export type CollabStatus = 'idle' | 'connecting' | 'open' | 'closed'

const ZOOM_MIN = 0.5
const ZOOM_MAX = 3.0

function clampZoom(z: number): number {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(z * 100) / 100))
}

export function useCollabSocket(
  spaceId: number,
  pictureId: number,
  userId: number,
  initialEditState: PictureEditState,
) {
  const status = ref<CollabStatus>('idle')
  const editState = ref<PictureEditState>({ ...initialEditState })
  const editorUser = ref<{ id: number; name?: string; username?: string } | null>(null)
  const isEditing = ref(false) // 我是否持有编辑锁

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let closed = false // 是否手动断开（手动断开不重连）

  function wsUrl(): string {
    const proto = location.protocol === 'https:' ? 'wss://' : 'ws://'
    const base = import.meta.env.VITE_API_BASE ?? '/api/v1'
    return `${proto}${location.host}${base}/spaces/${spaceId}/pictures/${pictureId}/collab`
  }

  function send(payload: Record<string, unknown>): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload))
    }
  }

  function connect(): void {
    if (ws) return
    closed = false
    status.value = 'connecting'
    ws = new WebSocket(wsUrl())
    ws.onopen = () => {
      status.value = 'open'
    }
    ws.onmessage = (e) => handleMessage(e.data)
    ws.onerror = () => {
      status.value = 'closed'
    }
    ws.onclose = () => {
      status.value = 'closed'
      ws = null
      isEditing.value = false
      editorUser.value = null
      if (!closed) {
        reconnectTimer = setTimeout(connect, 2000)
      }
    }
  }

  function disconnect(): void {
    closed = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    status.value = 'idle'
    isEditing.value = false
    editorUser.value = null
  }

  // 应用服务端下发的状态：仅非默认（或来自 EDIT_ACTION 强制）时才覆盖，避免覆盖已保存的初始态
  function applyServerState(s: Partial<PictureEditState> | null, force: boolean): void {
    if (!s) return
    const state: PictureEditState = {
      rotation: s.rotation ?? 0,
      zoom: s.zoom ?? 1.0,
      crop: s.crop ?? null,
    }
    if (force || state.rotation !== 0 || state.crop !== null) {
      editState.value = state
    }
  }

  function handleMessage(raw: string): void {
    let msg: { type: string; message?: string; edit_action?: string; edit_state?: PictureEditState | null; user?: { id: number; name?: string; username?: string } }
    try {
      msg = JSON.parse(raw)
    } catch {
      return
    }
    switch (msg.type) {
      case 'INFO':
        applyServerState(msg.edit_state ?? null, false)
        break
      case 'EDIT_ACTION':
        applyServerState(msg.edit_state ?? null, true)
        break
      case 'ENTER_EDIT':
        editorUser.value = msg.user ?? null
        if (msg.user?.id === userId) isEditing.value = true
        break
      case 'EXIT_EDIT':
        editorUser.value = null
        isEditing.value = false
        break
      case 'ERROR':
        ElMessage.warning(msg.message || '操作失败')
        break
    }
  }

  // ---- 动作 ----
  function applyAction(action: string, next: PictureEditState): void {
    editState.value = next
    send({ type: 'EDIT_ACTION', edit_action: action, edit_state: next })
  }

  function enterEdit(): void {
    send({ type: 'ENTER_EDIT' })
  }
  function exitEdit(): void {
    send({ type: 'EXIT_EDIT' })
  }
  function zoomIn(): void {
    applyAction('ZOOM_IN', { ...editState.value, zoom: clampZoom(editState.value.zoom + 0.25) })
  }
  function zoomOut(): void {
    applyAction('ZOOM_OUT', { ...editState.value, zoom: clampZoom(editState.value.zoom - 0.25) })
  }
  function rotateLeft(): void {
    applyAction('ROTATE_LEFT', { ...editState.value, rotation: (editState.value.rotation - 90 + 360) % 360 })
  }
  function rotateRight(): void {
    applyAction('ROTATE_RIGHT', { ...editState.value, rotation: (editState.value.rotation + 90) % 360 })
  }
  function crop(rect: CropRect | null): void {
    applyAction('CROP', { ...editState.value, crop: rect })
  }
  function save(): void {
    send({ type: 'SAVE', edit_state: { rotation: editState.value.rotation, crop: editState.value.crop } })
  }

  return {
    status,
    editState,
    editorUser,
    isEditing,
    connect,
    disconnect,
    enterEdit,
    exitEdit,
    zoomIn,
    zoomOut,
    rotateLeft,
    rotateRight,
    crop,
    save,
  }
}
