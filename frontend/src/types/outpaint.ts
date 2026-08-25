/**
 * AI 扩图（图像画面扩展）相关类型，对齐后端 Pydantic（snake_case）
 */

export type OutpaintOutputRatio = '' | '1:1' | '3:4' | '4:3' | '9:16' | '16:9'

export type TaskStatus = 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELED' | 'UNKNOWN'

/** 扩图参数（全部可选，未设置则不传，由后端按默认值处理） */
export interface OutpaintingParameters {
  angle?: number // 逆时针旋转角度 0-359
  output_ratio?: OutpaintOutputRatio // 输出宽高比
  x_scale?: number // 水平方向按比例扩展 1.0-3.0
  y_scale?: number // 垂直方向按比例扩展 1.0-3.0
  top_offset?: number // 上方添加像素
  bottom_offset?: number // 下方添加像素
  left_offset?: number // 左侧添加像素
  right_offset?: number // 右侧添加像素
  best_quality?: boolean // 最佳质量模式
  limit_image_size?: boolean // 限制输出文件大小
  add_watermark?: boolean // 添加 AI 水印
}

/** 创建扩图任务响应 */
export interface CreateTaskResponse {
  task_id: string
  task_status: string
}

/** 查询扩图任务响应（前端轮询） */
export interface QueryTaskResponse {
  task_id: string
  task_status: string
  output_image_url: string | null
  code: string | null
  message: string | null
}
