/**
 * 空间模块 API
 */
import { http } from './http'
import type {
  ColorSearchItem,
  SpaceCreatePayload,
  SpaceInfoRead,
  SpaceListParams,
  SpaceListResponse,
  SpaceRead,
  SpaceUpdatePayload,
} from '@/types/space'
import type {
  PictureListParams,
  PictureListResponse,
  PictureRead,
  PictureUpdatePayload,
} from '@/types/picture'
import type { ImageSearchResponse } from '@/types/search'
import type { MessageResponse } from '@/types/user'

export const spaceApi = {
  // ---- 用户：空间 ----
  /** 创建私有空间（每用户仅一个） */
  create(payload: SpaceCreatePayload): Promise<SpaceRead> {
    return http.post<SpaceRead>('/spaces/', payload).then((r) => r.data)
  },

  /** 我的空间信息（含剩余量） */
  getMy(): Promise<SpaceInfoRead> {
    return http.get<SpaceInfoRead>('/spaces/my').then((r) => r.data)
  },

  /** 升级/降级空间级别 */
  changeLevel(space_level: number): Promise<SpaceInfoRead> {
    return http.patch<SpaceInfoRead>('/spaces/my/level', { space_level }).then((r) => r.data)
  },

  // ---- 管理员：空间 ----
  list(params: SpaceListParams = {}): Promise<SpaceListResponse> {
    return http.get<SpaceListResponse>('/spaces/', { params }).then((r) => r.data)
  },

  get(id: number): Promise<SpaceRead> {
    return http.get<SpaceRead>(`/spaces/${id}`).then((r) => r.data)
  },

  update(id: number, payload: SpaceUpdatePayload): Promise<SpaceRead> {
    return http.patch<SpaceRead>(`/spaces/${id}`, payload).then((r) => r.data)
  },

  remove(id: number): Promise<MessageResponse> {
    return http.delete<MessageResponse>(`/spaces/${id}`).then((r) => r.data)
  },

  ban(id: number): Promise<SpaceRead> {
    return http.post<SpaceRead>(`/spaces/${id}/ban`).then((r) => r.data)
  },

  unban(id: number): Promise<SpaceRead> {
    return http.post<SpaceRead>(`/spaces/${id}/unban`).then((r) => r.data)
  },

  // ---- 用户：空间图片（仅自己空间） ----
  listPictures(params: PictureListParams = {}): Promise<PictureListResponse> {
    return http.get<PictureListResponse>('/spaces/my/pictures', { params }).then((r) => r.data)
  },

  uploadPicture(formData: FormData): Promise<PictureRead> {
    return http.post<PictureRead>('/spaces/my/pictures', formData).then((r) => r.data)
  },

  getPicture(id: number): Promise<PictureRead> {
    return http.get<PictureRead>(`/spaces/my/pictures/${id}`).then((r) => r.data)
  },

  /** 以图搜图（对空间内图片搜相似） */
  similar(id: number): Promise<ImageSearchResponse> {
    return http.get<ImageSearchResponse>(`/spaces/my/pictures/${id}/similar`).then((r) => r.data)
  },

  /** 按颜色搜索（颜色支持 #RRGGBB，返回按距离升序） */
  searchByColor(params: { color: string; limit?: number }): Promise<ColorSearchItem[]> {
    return http
      .get<ColorSearchItem[]>('/spaces/my/pictures/search-by-color', { params })
      .then((r) => r.data)
  },

  updatePicture(id: number, payload: PictureUpdatePayload): Promise<MessageResponse> {
    return http.patch<MessageResponse>(`/spaces/my/pictures/${id}`, payload).then((r) => r.data)
  },

  removePicture(id: number): Promise<MessageResponse> {
    return http.delete<MessageResponse>(`/spaces/my/pictures/${id}`).then((r) => r.data)
  },
}
