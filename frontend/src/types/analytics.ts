/**
 * 图库分析相关类型，对齐后端 Pydantic（snake_case）
 */

export type Granularity = 'day' | 'week' | 'month'

/** 公共图库总量统计 */
export interface GalleryOverview {
  total_pictures: number
  total_size: number
  total_downloads: number
}

/** 上传量趋势数据点 */
export interface TrendPoint {
  period: string
  count: number
}

/** 存储容量趋势数据点 */
export interface StorageTrendPoint {
  period: string
  total_size: number
}

/** 分类分布项 */
export interface CategoryStat {
  category: string
  count: number
  total_size: number
  ratio: number
}

/** 标签项 */
export interface TagStat {
  tag: string
  count: number
}

/** 上传者排行项 */
export interface TopUploader {
  user_id: number
  name: string | null
  username: string
  count: number
}

/** 空间大盘（管理员） */
export interface SpacesOverview {
  total_spaces: number
  total_capacity: number
  total_used: number
  usage_rate: number
  avg_pictures_per_space: number
}

/** 空间排行项 */
export interface SpaceRankItem {
  space_id: number
  name: string
  user_id: number
  username: string
  space_level: number
  total_count: number
  total_size: number
}

/** 个人空间摘要 */
export interface MySpaceOverview {
  space_id: number | null
  picture_count: number
  max_count: number
  count_usage: number
  total_size: number
  max_size: number
  size_usage: number
}

/** 个人热门图片项 */
export interface MyTopPicture {
  picture_id: number
  name: string
  url: string
  download_count: number
}
