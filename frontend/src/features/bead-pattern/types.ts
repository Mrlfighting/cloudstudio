/** 拼豆工具自己的领域协议，不引用图库数据库类型。 */
export const PALETTE_REVISION = "178dafbc9e77d3de556550dbd058270200129186";
export const ENGINE_VERSION = "ciede2000-lanczos3-v1";
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const MAX_SOURCE_PIXELS = 25_000_000;
export interface BeadColor {
  code: string;
  hex: string;
}
export interface BeadPalette {
  id: string;
  name: string;
  nominalCount: number;
  colors: BeadColor[];
}
export interface GenerationParams {
  longEdge: number;
  maxColors: number;
  removeBackground: boolean;
  backgroundColor: string | null;
  tolerance: number;
  denoise: 0 | 1 | 2;
}
export const DEFAULT_PARAMS: GenerationParams = {
  longEdge: 100,
  maxColors: 40,
  removeBackground: false,
  backgroundColor: null,
  tolerance: 8,
  denoise: 0,
};
/** 网格按行存储色卡索引；-1 表示无需放豆的空格。 */
export interface BeadPattern {
  width: number;
  height: number;
  cells: number[];
}
export interface BeadPatternProject {
  format: "cloudatelier-bead-pattern";
  version: 1;
  engineVersion: typeof ENGINE_VERSION;
  paletteRevision: typeof PALETTE_REVISION;
  paletteId: string;
  name: string;
  updatedAt: string;
  params: GenerationParams;
  pattern: BeadPattern;
}
export interface BeadUsage extends BeadColor {
  index: number;
  count: number;
}
export interface GenerationOutput {
  pattern: BeadPattern;
  warnings: string[];
  durationMs: number;
}
/** 本地工作源仅为缩小图片；不保存远端 URL、账号令牌或图库对象。 */
export interface BeadDraft {
  id: string;
  owner: string;
  project: BeadPatternProject;
  source: Blob | null;
  thumbnail: string | null;
  createdAt?: string;
  editingParams?: GenerationParams;
  editingPaletteId?: string;
  cloud?: CloudLink;
  cloudClientId?: string;
}

/** 云端关联只留在账号缓存，不写入可分享的 JSON 备份。 */
export interface CloudLink {
  id: string;
  revision: number;
  clientId: string;
}
export interface BeadWorkspace {
  owner: string;
  draftId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  params: GenerationParams;
  paletteId: string;
  project: BeadPatternProject | null;
  source: Blob | null;
  sourceSize: { width: number; height: number };
  cloud?: CloudLink;
  cloudClientId?: string;
}
export interface CloudItem {
  id: string;
  client_id: string;
  name: string;
  revision: number;
  created_at: string;
  updated_at: string;
  width: number;
  height: number;
  palette_id: string;
  has_source: boolean;
  has_thumbnail: boolean;
}
export interface CloudDetail extends CloudItem {
  project_data: BeadPatternProject;
}
export interface MigrationRecord {
  key: string;
  owner: string;
  sourceId: string;
  fingerprint: string;
  cloud: CloudLink;
}

/** 冻结一次待确认创建；网络重试/刷新后复用标识、参数和图片，不重新发起新建意图。 */
export interface PendingCloudCreate {
  key: string;
  owner: string;
  draftId: string;
  scope: "workshop" | "migration";
  clientId: string;
  asNew: boolean;
  project: BeadPatternProject;
  source: Blob | null;
  thumbnail: string | null;
}
