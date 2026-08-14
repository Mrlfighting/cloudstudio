/**
 * 图片模块类型定义（镜像后端 Pydantic Schema）
 */
import type { PaginatedResponse } from '@/types/user'

export type PictureStatus = 'pending' | 'approved' | 'rejected'
export type PictureSort = 'time' | 'popularity'

/** 预置分类（与后端 PictureCategory 完全一致） */
export const PICTURE_CATEGORIES = ['风景', '人物', '动物', '建筑', '美食', '科技', '插画', '其他'] as const
export type PictureCategory = (typeof PICTURE_CATEGORIES)[number]

/** 图片完整信息（详情，GET /pictures/{id}） */
export interface PictureRead {
  id: number
  url: string
  name: string
  introduction: string | null
  category: string | null
  tags: string[]
  pic_size: number | null
  pic_width: number | null
  pic_height: number | null
  pic_scale: number | null
  pic_format: string | null
  color_mode: string | null
  user_id: number
  status: PictureStatus
  review_reason: string | null
  download_count: number
  created_at: string | null
  updated_at: string | null
}

/** 图片列表项（精简，无 introduction / pic_scale / color_mode 等） */
export interface PictureListItemRead {
  id: number
  url: string
  name: string
  category: string | null
  tags: string[]
  pic_width: number | null
  pic_height: number | null
  pic_format: string | null
  status: PictureStatus
  review_reason: string | null
  user_id: number
  download_count: number
  created_at: string | null
}

/** 列表/管理共用查询参数（snake_case 直接对齐后端 Query） */
export interface PictureListParams {
  page?: number
  items_per_page?: number
  category?: string
  keyword?: string
  sort?: PictureSort
  /** 仅管理端使用 */
  status?: PictureStatus
}

/** PATCH /pictures/{id} —— tags 是数组（JSON body） */
export interface PictureUpdatePayload {
  name?: string
  introduction?: string
  category?: PictureCategory
  tags?: string[]
}

export type PictureListResponse = PaginatedResponse<PictureListItemRead>
