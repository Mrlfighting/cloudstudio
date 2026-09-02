/**
 * 图片模块类型定义（镜像后端 Pydantic Schema）
 */
import type { PaginatedResponse } from '@/types/user'

export type PictureStatus = 'pending' | 'approved' | 'rejected'
export type PictureSort = 'time' | 'popularity'

/** 图片所属场景：公共图库 / 私有空间 / 团队空间（用于图片卡片/上传/编辑弹窗多态） */
export type PictureKind = 'picture' | 'space' | 'team'

/** 裁剪矩形（原图像素坐标，非破坏性） */
export interface CropRect {
  x: number
  y: number
  width: number
  height: number
}

/** 图片编辑状态（协同编辑视图状态；zoom 仅视图不落库） */
export interface PictureEditState {
  rotation: number
  zoom: number
  crop: CropRect | null
}

/** 落库的编辑参数（无 zoom，对齐后端 pictures.edit_state） */
export interface PersistedEditState {
  rotation: number
  crop: CropRect | null
}

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
  edit_state: PersistedEditState | null
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
