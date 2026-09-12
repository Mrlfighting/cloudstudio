/**
 * 图库分析 API
 */
import { http } from './http'
import type {
  CategoryStat,
  GalleryOverview,
  Granularity,
  MySpaceOverview,
  MyTopPicture,
  SpaceRankItem,
  SpacesOverview,
  StorageTrendPoint,
  TagStat,
  TopUploader,
  TrendPoint,
} from '@/types/analytics'

export const analyticsApi = {
  // ---- 管理员：公共图库分析 ----
  /** 公共图库总量统计 */
  galleryOverview(): Promise<GalleryOverview> {
    return http.get<GalleryOverview>('/analytics/gallery/overview').then((r) => r.data)
  },

  /** 上传量增长趋势（按日/周/月） */
  galleryTrend(granularity: Granularity): Promise<TrendPoint[]> {
    return http
      .get<TrendPoint[]>('/analytics/gallery/trend', { params: { granularity } })
      .then((r) => r.data)
  },

  /** 分类分布 */
  galleryCategory(): Promise<CategoryStat[]> {
    return http.get<CategoryStat[]>('/analytics/gallery/category').then((r) => r.data)
  },

  /** 热门标签 TOP N */
  galleryTags(limit = 20): Promise<TagStat[]> {
    return http
      .get<TagStat[]>('/analytics/gallery/tags', { params: { limit } })
      .then((r) => r.data)
  },

  /** 上传者排行 TOP N */
  topUploaders(limit = 10): Promise<TopUploader[]> {
    return http
      .get<TopUploader[]>('/analytics/gallery/top-uploaders', { params: { limit } })
      .then((r) => r.data)
  },

  /** 存储容量趋势（按日/周/月） */
  galleryStorageTrend(granularity: Granularity): Promise<StorageTrendPoint[]> {
    return http
      .get<StorageTrendPoint[]>('/analytics/gallery/storage-trend', { params: { granularity } })
      .then((r) => r.data)
  },

  // ---- 管理员：空间大盘 ----
  /** 空间大盘 */
  spacesOverview(): Promise<SpacesOverview> {
    return http.get<SpacesOverview>('/analytics/spaces/overview').then((r) => r.data)
  },

  /** 空间排行 TOP N（按数量或容量） */
  spacesRanking(limit = 10, sort: 'count' | 'size' = 'count'): Promise<SpaceRankItem[]> {
    return http
      .get<SpaceRankItem[]>('/analytics/spaces/ranking', { params: { limit, sort } })
      .then((r) => r.data)
  },

  // ---- 用户：我的空间分析 ----
  /** 个人空间摘要 */
  myOverview(): Promise<MySpaceOverview> {
    return http.get<MySpaceOverview>('/analytics/my/overview').then((r) => r.data)
  },

  /** 个人上传趋势（按日/周/月） */
  myTrend(granularity: Granularity): Promise<TrendPoint[]> {
    return http
      .get<TrendPoint[]>('/analytics/my/trend', { params: { granularity } })
      .then((r) => r.data)
  },

  /** 个人热门图片 TOP N */
  myTopPictures(limit = 10): Promise<MyTopPicture[]> {
    return http
      .get<MyTopPicture[]>('/analytics/my/top-pictures', { params: { limit } })
      .then((r) => r.data)
  },

  /** 个人分类分布 */
  myCategory(): Promise<CategoryStat[]> {
    return http.get<CategoryStat[]>('/analytics/my/category').then((r) => r.data)
  },

  /** 个人标签分布 TOP N */
  myTags(limit = 20): Promise<TagStat[]> {
    return http
      .get<TagStat[]>('/analytics/my/tags', { params: { limit } })
      .then((r) => r.data)
  },
}
