/** 独立确定性算法：复用 MIT Culori 的 Lab D65 与 CIEDE2000，不复制 AGPL 实现。 */
import { converter, differenceCiede2000 } from "culori";
import type { Lab65 } from "culori";
import type {
  BeadColor,
  BeadPattern,
  BeadUsage,
  GenerationParams,
} from "./types.ts";

const toLab = converter("lab65");
const delta = differenceCiede2000();
export const deltaE = (a: Lab65, b: Lab65): number => delta(a, b);

/** 以最长边格数控制规模，另一边按比例取整，不拉伸原图。 */
export function gridSize(
  width: number,
  height: number,
  longEdge: number,
): { width: number; height: number } {
  if (
    !(width > 0 && height > 0) ||
    !Number.isInteger(longEdge) ||
    longEdge < 20 ||
    longEdge > 200
  )
    throw new Error("图纸尺寸无效");
  const scale = longEdge / Math.max(width, height);
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

/** 原始 RGB 只转换一次，色卡的 Lab 在整次生成中复用。 */
function labOf(r: number, g: number, b: number): Lab65 {
  return toLab({ mode: "rgb", r: r / 255, g: g / 255, b: b / 255 });
}

/** 仅遍历四邻域，避免斜角相连时误吞封闭区域。 */
function neighbors(index: number, width: number, height: number): number[] {
  const x = index % width,
    y = Math.floor(index / width);
  const values: number[] = [];
  if (x > 0) values.push(index - 1);
  if (x + 1 < width) values.push(index + 1);
  if (y > 0) values.push(index - width);
  if (y + 1 < height) values.push(index + width);
  return values;
}

/** 从固定背景原型洪泛，不沿渐变逐格漂移；透明区域允许通行。 */
function backgroundMask(
  rgba: Uint8ClampedArray,
  width: number,
  height: number,
  params: GenerationParams,
): { active: Uint8Array; warning?: string } {
  const n = width * height,
    active = new Uint8Array(n);
  const labs = new Map<number, Lab65>();
  const at = (i: number) => {
    let lab = labs.get(i);
    if (!lab) {
      lab = labOf(rgba[i * 4]!, rgba[i * 4 + 1]!, rgba[i * 4 + 2]!);
      labs.set(i, lab);
    }
    return lab;
  };
  for (let i = 0; i < n; i++) active[i] = rgba[i * 4 + 3]! >= 128 ? 1 : 0;
  if (!params.removeBackground) return { active };
  let prototype = params.backgroundColor
    ? toLab(params.backgroundColor)
    : undefined;
  if (!prototype) {
    const corners = [
      ...new Set([0, width - 1, (height - 1) * width, n - 1]),
    ].filter((i) => active[i]);
    let best = 0;
    for (const i of corners) {
      const votes = corners.filter(
        (j) => delta(at(i), at(j)) <= params.tolerance,
      ).length;
      if (votes > best) {
        best = votes;
        prototype = at(i);
      }
    }
    if (corners.length === 0 || best <= corners.length / 2)
      return {
        active,
        warning: "四角背景不一致，未自动去除；可手动指定背景色。",
      };
  }
  const visited = new Uint8Array(n),
    queue: number[] = [];
  const seed = (i: number) => {
    if (visited[i]) return;
    visited[i] = 1;
    if (!active[i] || delta(at(i), prototype!) <= params.tolerance) {
      active[i] = 0;
      queue.push(i);
    }
  };
  for (let x = 0; x < width; x++) {
    seed(x);
    seed((height - 1) * width + x);
  }
  for (let y = 0; y < height; y++) {
    seed(y * width);
    seed(y * width + width - 1);
  }
  for (let head = 0; head < queue.length; head++)
    for (const next of neighbors(queue[head]!, width, height)) seed(next);
  return { active };
}

/** 低频颜色逐次合并到最近的现存色，确保硬性满足最多 K 色。 */
export function limitColors(
  cells: number[],
  colors: BeadColor[],
  maximum: number,
): number[] {
  const counts = new Map<number, number>();
  for (const cell of cells)
    if (cell >= 0) counts.set(cell, (counts.get(cell) ?? 0) + 1);
  const labs = colors.map((color) => toLab(color.hex));
  const replacements = new Map<number, number>(),
    distances = new Map<string, number>();
  const distance = (a: number, b: number) => {
    const key = a < b ? `${a}:${b}` : `${b}:${a}`;
    let value = distances.get(key);
    if (value === undefined) {
      value = delta(labs[a]!, labs[b]!);
      distances.set(key, value);
    }
    return value;
  };
  while (counts.size > maximum) {
    const sorted = [...counts.keys()].sort(
      (a, b) => counts.get(a)! - counts.get(b)! || a - b,
    );
    const source = sorted[0]!;
    let target = sorted[1]!,
      best = Infinity;
    for (const candidate of sorted.slice(1)) {
      const value = distance(source, candidate);
      if (value < best || (value === best && candidate < target)) {
        target = candidate;
        best = value;
      }
    }
    replacements.set(source, target);
    counts.set(target, counts.get(target)! + counts.get(source)!);
    counts.delete(source);
  }
  return cells.map((cell) => {
    let result = cell;
    while (replacements.has(result)) result = replacements.get(result)!;
    return result;
  });
}

/** 一次性处理小连通块，使用原始网格判断，避免级联抹除细节。 */
export function cleanSpeckles(
  pattern: BeadPattern,
  colors: BeadColor[],
  size: number,
): number[] {
  if (!size) return pattern.cells.slice();
  const { width, height, cells } = pattern,
    next = cells.slice(),
    seen = new Uint8Array(cells.length);
  const labs = colors.map((color) => toLab(color.hex));
  for (let i = 0; i < cells.length; i++) {
    if (seen[i] || cells[i]! < 0) continue;
    const component = [i],
      borders = new Map<number, number>();
    seen[i] = 1;
    for (let head = 0; head < component.length; head++) {
      for (const j of neighbors(component[head]!, width, height)) {
        if (cells[j] === cells[i]) {
          if (!seen[j]) {
            seen[j] = 1;
            component.push(j);
          }
        } else if (cells[j]! >= 0)
          borders.set(cells[j]!, (borders.get(cells[j]!) ?? 0) + 1);
      }
    }
    if (component.length > size || !borders.size) continue;
    const replacement = [...borders.keys()].sort(
      (a, b) =>
        borders.get(b)! - borders.get(a)! ||
        delta(labs[cells[i]!]!, labs[a]!) - delta(labs[cells[i]!]!, labs[b]!) ||
        a - b,
    )[0]!;
    for (const j of component) next[j] = replacement;
  }
  return next;
}

/** 转换仅接收已完成 LANCZOS 缩放的有界 RGBA，便于独立测试。 */
export function mapPattern(
  rgba: Uint8ClampedArray,
  width: number,
  height: number,
  colors: BeadColor[],
  params: GenerationParams,
  progress: (value: number) => void = () => {},
): { pattern: BeadPattern; warnings: string[] } {
  if (
    !colors.length ||
    rgba.length !== width * height * 4 ||
    width * height > 40_000 ||
    width < 1 ||
    height < 1
  )
    throw new Error("转换输入无效");
  if (
    !Number.isInteger(params.maxColors) ||
    params.maxColors < 2 ||
    params.maxColors > 128
  )
    throw new Error("最多颜色数应为 2–128");
  const { active, warning } = backgroundMask(rgba, width, height, params);
  const labs = colors.map((color) => toLab(color.hex)),
    cache = new Map<number, number>();
  let cells = Array<number>(width * height).fill(-1);
  for (let i = 0; i < cells.length; i++) {
    if (!active[i]) continue;
    const r = rgba[i * 4]!,
      g = rgba[i * 4 + 1]!,
      b = rgba[i * 4 + 2]!,
      key = (r << 16) | (g << 8) | b;
    let matched = cache.get(key);
    if (matched === undefined) {
      const lab = labOf(r, g, b);
      let best = Infinity;
      matched = 0;
      for (let j = 0; j < labs.length; j++) {
        const d = delta(lab, labs[j]!);
        if (d < best) {
          best = d;
          matched = j;
        }
      }
      cache.set(key, matched);
    }
    cells[i] = matched;
    if (i % 1024 === 0) progress(25 + Math.round((i / cells.length) * 50));
  }
  progress(80);
  cells = limitColors(cells, colors, params.maxColors);
  progress(90);
  cells = cleanSpeckles({ width, height, cells }, colors, params.denoise);
  // 去杂只允许使用既存色，但相邻小块交换也可能保留原色；再次限色保证不变量。
  cells = limitColors(cells, colors, params.maxColors);
  progress(100);
  return {
    pattern: { width, height, cells },
    warnings: warning ? [warning] : [],
  };
}

/** 预览、清单与导出统一按最终网格统计，空格不计数。 */
export function usageOf(
  pattern: BeadPattern,
  colors: BeadColor[],
): BeadUsage[] {
  const counts = new Map<number, number>();
  for (const index of pattern.cells)
    if (index >= 0) counts.set(index, (counts.get(index) ?? 0) + 1);
  return [...counts]
    .map(([index, count]) => ({ ...colors[index]!, index, count }))
    .sort((a, b) => b.count - a.count || a.index - b.index);
}
