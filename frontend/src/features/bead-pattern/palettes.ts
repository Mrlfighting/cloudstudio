/** 色卡直接取得自 MIT 上游；来源与原始字节校验记录见 palettes/sources.json。 */
import mard from "./palettes/mard-291-github.json" with { type: "json" };
import coco from "./palettes/coco-291.json" with { type: "json" };
import manman from "./palettes/manman-278.json" with { type: "json" };
import panpan from "./palettes/panpan-289.json" with { type: "json" };
import mixiaowo from "./palettes/mixiaowo-290.json" with { type: "json" };
import type { BeadColor, BeadPalette } from "./types.ts";

/** 无法采购的色号、透明色和同一 HEX 的后续别名不进入转换引擎。 */
export function usableColors(
  raw: readonly {
    code: string;
    hex: string;
    unidentified?: boolean;
    transparency?: string;
  }[],
): BeadColor[] {
  const seen = new Set<string>();
  return raw.flatMap((item) => {
    const code = item.code.trim(),
      hex = item.hex.toUpperCase();
    if (
      !code ||
      /^(-|\?|UNKNOWN.*)$/i.test(code) ||
      item.unidentified ||
      item.transparency ||
      !/^#[0-9A-F]{6}$/.test(hex) ||
      seen.has(hex)
    )
      return [];
    seen.add(hex);
    return [{ code, hex }];
  });
}
export const PALETTES: BeadPalette[] = [
  { raw: mard, name: "MARD" },
  { raw: coco, name: "COCO" },
  { raw: manman, name: "漫漫" },
  { raw: panpan, name: "盼盼" },
  { raw: mixiaowo, name: "咪小窝" },
].map(({ raw, name }) => ({
  id: raw.id,
  name,
  nominalCount: raw.count,
  colors: usableColors(raw.colors),
}));

export function getPalette(id: string): BeadPalette {
  const palette = PALETTES.find((item) => item.id === id);
  if (!palette) throw new Error("未知色卡，请选择受支持的品牌");
  return palette;
}
