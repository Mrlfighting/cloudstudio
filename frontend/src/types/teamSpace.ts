/**
 * 团队空间模块类型定义（镜像后端 Pydantic Schema，snake_case 对齐）
 */

/** 团队成员角色（对齐后端 SpaceRole） */
export type SpaceRole = 'admin' | 'editor' | 'viewer'

/** 角色选项常量（用于下拉） */
export const SPACE_ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'editor', label: '编辑者' },
  { value: 'viewer', label: '查看者' },
] as const

/** 角色值 → 中文标签 */
export function spaceRoleLabel(role: string): string {
  return SPACE_ROLE_OPTIONS.find((o) => o.value === role)?.label ?? `未知(${role})`
}

/** 我加入（含我创建）的团队空间列表项（GET /spaces/team/joined，待后端补充） */
export interface TeamSpaceListItemRead {
  id: number
  name: string
  space_role: SpaceRole
  space_level: number
  total_count: number
  total_size: number
  max_count: number
  max_size: number
  created_at: string | null
}

/** 团队成员（GET /spaces/{id}/members） */
export interface SpaceMemberRead {
  user_id: number
  username: string
  name: string
  space_role: SpaceRole
  created_at: string | null
}

/** 邀请成员入参（POST /spaces/{id}/members） */
export interface SpaceMemberCreatePayload {
  user_id: number
  space_role: SpaceRole
}

/** 设置成员角色入参（PATCH /spaces/{id}/members/{user_id}） */
export interface SpaceMemberUpdatePayload {
  space_role: SpaceRole
}

/** 团队空间设置入参（PATCH /spaces/{id}/settings） */
export interface TeamSpaceSettingsPayload {
  name?: string
  space_level?: number
}
