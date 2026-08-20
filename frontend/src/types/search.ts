/**
 * 以图搜图类型定义（镜像后端 infrastructure/image_search/models.py）
 */

/** 单条相似图片结果 */
export interface SearchResult {
  thumbnail_url: string
  source_url: string
  source_name: string
  title: string | null
  score: number | null
}

/** 单个搜索源的结果组 */
export interface SourceSearchResult {
  source_name: string
  results: SearchResult[]
  error: string | null
  skipped: boolean
}

/** 以图搜图聚合响应 */
export interface ImageSearchResponse {
  query_url: string
  sources: SourceSearchResult[]
}
