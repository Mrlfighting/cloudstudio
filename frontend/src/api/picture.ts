/**
 * 图片模块 API
 */
import { http } from './http'
import type {
  PictureListParams,
  PictureListResponse,
  PictureRead,
  PictureUpdatePayload,
} from '@/types/picture'
import type { MessageResponse } from '@/types/user'

export const pictureApi = {
  /** 用户端列表（已发布）—— 注意末尾斜杠 */
  list(params: PictureListParams = {}): Promise<PictureListResponse> {
    return http.get<PictureListResponse>('/pictures/', { params }).then((r) => r.data)
  },

  /** 管理端列表（全状态）—— 无斜杠 */
  manage(params: PictureListParams = {}): Promise<PictureListResponse> {
    return http.get<PictureListResponse>('/pictures/manage', { params }).then((r) => r.data)
  },

  /** 图片详情（仅已发布） */
  get(id: number): Promise<PictureRead> {
    return http.get<PictureRead>(`/pictures/${id}`).then((r) => r.data)
  },

  /** 下载：只构建 URL，用浏览器原生导航（302 重定向到 COS，不用 axios） */
  downloadUrl(id: number): string {
    const base = import.meta.env.VITE_API_BASE ?? '/api/v1'
    return `${base}/pictures/${id}/download`
  },

  /** 上传：multipart FormData；CSRF 头由拦截器自动注入；不手动设 Content-Type */
  upload(formData: FormData): Promise<PictureRead> {
    return http.post<PictureRead>('/pictures/', formData).then((r) => r.data)
  },

  /** 编辑图片元信息（tags 直接传数组，JSON body） */
  update(id: number, payload: PictureUpdatePayload): Promise<MessageResponse> {
    return http.patch<MessageResponse>(`/pictures/${id}`, payload).then((r) => r.data)
  },

  /** 审核图片 */
  audit(id: number, status: 'approved' | 'rejected'): Promise<MessageResponse> {
    return http
      .patch<MessageResponse>(`/pictures/${id}/status`, { status })
      .then((r) => r.data)
  },

  /** 软删除图片 */
  remove(id: number): Promise<MessageResponse> {
    return http.delete<MessageResponse>(`/pictures/${id}`).then((r) => r.data)
  },
}
