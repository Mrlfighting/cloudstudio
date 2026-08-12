/**
 * 用户模块 API
 */
import { http } from './http'
import type {
  ChangeRolePayload,
  MessageResponse,
  PaginatedResponse,
  UpdateProfilePayload,
  UserRead,
  UserRole,
} from '@/types/user'

export const userApi = {
  /** 获取当前用户（未登录 401） */
  getMe(): Promise<UserRead> {
    return http.get<UserRead>('/users/me').then((r) => r.data)
  },

  /** 修改个人信息（本人/管理员；重复账号/邮箱 422） */
  updateProfile(username: string, payload: UpdateProfilePayload): Promise<MessageResponse> {
    return http.patch<MessageResponse>(`/users/${username}`, payload).then((r) => r.data)
  },

  /** 管理员：分页用户列表（非管理员 403） */
  getUsers(page = 1, itemsPerPage = 10): Promise<PaginatedResponse<UserRead>> {
    return http
      .get<PaginatedResponse<UserRead>>('/users/', {
        params: { page, items_per_page: itemsPerPage },
      })
      .then((r) => r.data)
  },

  /** 管理员：修改用户角色 */
  changeRole(username: string, userRole: UserRole): Promise<MessageResponse> {
    const payload: ChangeRolePayload = { user_role: userRole }
    return http.patch<MessageResponse>(`/users/${username}/role`, payload).then((r) => r.data)
  },
}
