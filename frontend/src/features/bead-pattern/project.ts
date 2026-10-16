/** 项目文件为独立版本协议，只导出白名单字段，不含原图及远端 URL。 */
import { ENGINE_VERSION, PALETTE_REVISION } from "./types.ts";
import type { BeadPatternProject, GenerationParams } from "./types.ts";
import { getPalette } from "./palettes.ts";

export function validParams(value: unknown): value is GenerationParams {
  if (!value || typeof value !== "object") return false;
  const p = value as GenerationParams;
  return (
    Number.isInteger(p.longEdge) &&
    p.longEdge >= 20 &&
    p.longEdge <= 200 &&
    Number.isInteger(p.maxColors) &&
    p.maxColors >= 2 &&
    p.maxColors <= 128 &&
    typeof p.removeBackground === "boolean" &&
    (p.backgroundColor === null || /^#[\da-f]{6}$/i.test(p.backgroundColor)) &&
    Number.isFinite(p.tolerance) &&
    p.tolerance >= 0 &&
    p.tolerance <= 40 &&
    [0, 1, 2].includes(p.denoise)
  );
}

export function parseProject(value: unknown): BeadPatternProject {
  if (!value || typeof value !== "object") throw new Error("项目文件格式无效");
  const p = value as BeadPatternProject;
  if (
    p.format !== "cloudatelier-bead-pattern" ||
    p.version !== 1 ||
    p.engineVersion !== ENGINE_VERSION ||
    p.paletteRevision !== PALETTE_REVISION
  )
    throw new Error("项目版本或色卡版本不受支持");
  const palette = getPalette(p.paletteId);
  if (
    typeof p.name !== "string" ||
    !p.name.trim() ||
    p.name.length > 128 ||
    !validParams(p.params)
  )
    throw new Error("项目名称或参数无效");
  const pattern = p.pattern;
  if (
    !pattern ||
    !Number.isInteger(pattern.width) ||
    !Number.isInteger(pattern.height) ||
    pattern.width < 1 ||
    pattern.height < 1 ||
    pattern.width > 200 ||
    pattern.height > 200 ||
    !Array.isArray(pattern.cells) ||
    pattern.cells.length !== pattern.width * pattern.height ||
    pattern.cells.some(
      (i) => !Number.isInteger(i) || i < -1 || i >= palette.colors.length,
    ) ||
    new Set(pattern.cells.filter((i) => i >= 0)).size > p.params.maxColors
  )
    throw new Error("项目网格数据无效");
  if (
    typeof p.updatedAt !== "string" ||
    !Number.isFinite(Date.parse(p.updatedAt))
  )
    throw new Error("项目时间无效");
  // 显式重建对象，外部 JSON 中的附加字段永不进入本地存储或再次导出。
  return {
    format: p.format,
    version: 1,
    engineVersion: ENGINE_VERSION,
    paletteRevision: PALETTE_REVISION,
    paletteId: palette.id,
    name: p.name.trim(),
    updatedAt: p.updatedAt,
    params: {
      longEdge: p.params.longEdge,
      maxColors: p.params.maxColors,
      removeBackground: p.params.removeBackground,
      backgroundColor: p.params.backgroundColor,
      tolerance: p.params.tolerance,
      denoise: p.params.denoise,
    },
    pattern: {
      width: pattern.width,
      height: pattern.height,
      cells: [...pattern.cells],
    },
  };
}

export function projectJson(project: BeadPatternProject): string {
  return JSON.stringify(parseProject(project), null, 2);
}
