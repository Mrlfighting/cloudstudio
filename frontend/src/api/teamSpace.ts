/**
 * 团队空间模块 API
 */
import { http } from './http'
import type {
  SpaceMemberCreatePayload,
  SpaceMemberRead,
  SpaceMemberUpdatePayload,
  TeamSpaceListItemRead,
  TeamSpaceSettingsPayload,
} from '@/types/teamSpace'
import type { SpaceCreatePayload, SpaceInfoRead, SpaceRead } from '@/types/space'
import type {
  PictureListParams,
  PictureListResponse,
  PictureRead,
  PictureUpdatePayload,
} from '@/types/picture'
import type { MessageResponse } from '@/types/user'

export const teamSpaceApi = {
  // ---- 用户：团队空间 ----
  /** 我加入（含我创建）的团队空间列表 */
  listMyTeams(): Promise<TeamSpaceListItemRead[]> {
    return http.get<TeamSpaceListItemRead[]>('/spaces/team/joined').then((r) => r.data)
  },

  /** 创建团队空间（创建者自动成为管理员） */
  create(payload: SpaceCreatePayload): Promise<SpaceRead> {
    return http.post<SpaceRead>('/spaces/team', payload).then((r) => r.data)
  },

  /** 我创建的团队空间信息（含剩余配额） */
  getMyTeam(): Promise<SpaceInfoRead> {
    return http.get<SpaceInfoRead>('/spaces/team/my').then((r) => r.data)
  },

  /** 团队设置：改名 / 升级级别 */
  updateSettings(spaceId: number, payload: TeamSpaceSettingsPayload): Promise<SpaceRead> {
    return http.patch<SpaceRead>(`/spaces/${spaceId}/settings`, payload).then((r) => r.data)
  },

  // ---- 成员管理 ----
  listMembers(spaceId: number): Promise<SpaceMemberRead[]> {
    return http.get<SpaceMemberRead[]>(`/spaces/${spaceId}/members`).then((r) => r.data)
  },

  addMember(spaceId: number, payload: SpaceMemberCreatePayload): Promise<SpaceMemberRead> {
    return http.post<SpaceMemberRead>(`/spaces/${spaceId}/members`, payload).then((r) => r.data)
  },

  removeMember(spaceId: number, userId: number): Promise<MessageResponse> {
    return http.delete<MessageResponse>(`/spaces/${spaceId}/members/${userId}`).then((r) => r.data)
  },

  updateMemberRole(spaceId: number, userId: number, payload: SpaceMemberUpdatePayload): Promise<SpaceMemberRead> {
    return http.patch<SpaceMemberRead>(`/spaces/${spaceId}/members/${userId}`, payload).then((r) => r.data)
  },

  // ---- 团队空间图片 ----
  listPictures(spaceId: number, params: PictureListParams = {}): Promise<PictureListResponse> {
    return http.get<PictureListResponse>(`/spaces/${spaceId}/pictures`, { params }).then((r) => r.data)
  },

  uploadPicture(spaceId: number, formData: FormData): Promise<PictureRead> {
    return http.post<PictureRead>(`/spaces/${spaceId}/pictures`, formData).then((r) => r.data)
  },

  getPicture(spaceId: number, pictureId: number): Promise<PictureRead> {
    return http.get<PictureRead>(`/spaces/${spaceId}/pictures/${pictureId}`).then((r) => r.data)
  },

  updatePicture(spaceId: number, pictureId: number, payload: PictureUpdatePayload): Promise<MessageResponse> {
    return http.patch<MessageResponse>(`/spaces/${spaceId}/pictures/${pictureId}`, payload).then((r) => r.data)
  },

  removePicture(spaceId: number, pictureId: number): Promise<MessageResponse> {
    return http.delete<MessageResponse>(`/spaces/${spaceId}/pictures/${pictureId}`).then((r) => r.data)
  },
}
