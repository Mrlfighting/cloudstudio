/**
 * 用户模块类型定义（镜像后端 Pydantic Schema）
 */

export type UserRole = 'user' | 'admin'

/** GET /users/me 等返回的用户信息（对应后端 UserRead） */
export interface UserRead {
  id: number
  name: string
  username: string
  email: string | null
  profile_image_url: string
  user_profile: string | null
  is_deleted: boolean
  tier_id: number | null
  is_superuser: boolean
  user_role: UserRole
  email_verified: boolean
  oauth_provider: string | null
}

/** 注册入参（POST /users/register） */
export interface RegisterPayload {
  account: string
  password: string
  confirm_password: string
  nickname?: string
  user_profile?: string
}

/** 登录返回（POST /auth/login） */
export interface LoginResult {
  csrf_token: string
}

/** 检查登录态（GET /auth/check-auth） */
export interface CheckAuthResponse {
  authenticated: boolean
  user?: {
    id: number
    username: string
    email: string | null
    oauth_provider: string | null
  }
  session?: {
    created_at: string | null
    last_activity: string | null
  }
  message?: string
}

/** 修改个人信息入参（PATCH /users/{username}，字段均可选） */
export interface UpdateProfilePayload {
  name?: string
  username?: string
  email?: string | null
  profile_image_url?: string | null
  user_profile?: string | null
}

/** 修改角色入参（PATCH /users/{username}/role） */
export interface ChangeRolePayload {
  user_role: UserRole
}

/** 分页响应（fastcrud paginated_response 结构） */
export interface PaginatedResponse<T> {
  data: T[]
  total_count: number
  has_more: boolean
  page: number
  items_per_page: number
}

/** 后端返回的通用消息响应 */
export interface MessageResponse {
  message: string
}
