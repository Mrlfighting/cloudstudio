/**
 * 空间模块类型定义（镜像后端 Pydantic Schema）
 */
import type { PaginatedResponse } from '@/types/user'

export type SpaceLevel = 0 | 1 | 2
export type SpaceStatus = 'active' | 'banned'

/** 级别标签常量 */
export const SPACE_LEVEL_OPTIONS = [
  { value: 0, label: '普通版' },
  { value: 1, label: '专业版' },
  { value: 2, label: '旗舰版' },
] as const

/** 级别值 → 标签 */
export function spaceLevelLabel(level: number): string {
  return SPACE_LEVEL_OPTIONS.find((o) => o.value === level)?.label ?? `未知(${level})`
}

/** 字节 → 可读大小（B/KB/MB/GB） */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '未知'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

/** 空间完整信息（管理员详情，GET /spaces/{id}） */
export interface SpaceRead {
  id: number
  name: string
  space_level: SpaceLevel
  max_size: number
  max_count: number
  total_size: number
  total_count: number
  user_id: number
  status: SpaceStatus
  created_at: string | null
  updated_at: string | null
}

/** 空间列表项（管理员，GET /spaces/） */
export interface SpaceListItemRead {
  id: number
  name: string
  space_level: SpaceLevel
  max_size: number
  max_count: number
  total_size: number
  total_count: number
  user_id: number
  status: SpaceStatus
  created_at: string | null
}

/** 我的空间信息（含剩余量，GET /spaces/my） */
export interface SpaceInfoRead {
  id: number
  name: string
  space_level: SpaceLevel
  max_size: number
  max_count: number
  total_size: number
  total_count: number
  status: SpaceStatus
  remaining_size: number
  remaining_count: number
  created_at: string | null
}

/** 列表查询参数（snake_case 对齐后端 Query） */
export interface SpaceListParams {
  page?: number
  items_per_page?: number
  name?: string
  user_id?: number
  space_level?: SpaceLevel
}

/** POST /spaces/ 创建入参 */
export interface SpaceCreatePayload {
  name: string
}

/** PATCH /spaces/{id} 编辑入参 */
export interface SpaceUpdatePayload {
  name?: string
  space_level?: SpaceLevel
}

export type SpaceListResponse = PaginatedResponse<SpaceListItemRead>
