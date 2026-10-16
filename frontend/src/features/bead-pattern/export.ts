/** 统一按最终图纸渲染与统计；导出过程不读取原图，因此不会污染画布。 */
import { usageOf } from "./core.ts";
import { getPalette } from "./palettes.ts";
import { projectJson } from "./project.ts";
import type { BeadColor, BeadPattern, BeadPatternProject } from "./types.ts";

export function paintGrid(
  canvas: HTMLCanvasElement,
  pattern: BeadPattern,
  colors: BeadColor[],
  cell: number,
  codes = false,
  coordinates = false,
  title = "",
): void {
  const left = coordinates ? 42 : 0,
    top = coordinates ? 76 : 0;
  canvas.width = pattern.width * cell + left + (coordinates ? 20 : 0);
  canvas.height = pattern.height * cell + top + (coordinates ? 24 : 0);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("当前浏览器无法绘制图纸");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (coordinates) {
    ctx.fillStyle = "#252936";
    ctx.font = "bold 20px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(title, 18, 28, canvas.width - 36);
    ctx.font = "12px sans-serif";
    ctx.fillText(
      `${pattern.width} × ${pattern.height} 格 · 空白格无需放豆`,
      18,
      49,
    );
  }
  // 预览采用一次像素缓冲区拷贝与缩放，避免主线程逐格发出四万次 fillRect。
  const small = document.createElement("canvas");
  small.width = pattern.width;
  small.height = pattern.height;
  const smallCtx = small.getContext("2d");
  if (!smallCtx) throw new Error("当前浏览器无法绘制图纸");
  const pixels = smallCtx.createImageData(pattern.width, pattern.height);
  const rgbColors = colors.map((color) => parseInt(color.hex.slice(1), 16));
  for (let i = 0; i < pattern.cells.length; i++) {
    const rgb = rgbColors[pattern.cells[i]!] ?? 0xf4f5f8;
    pixels.data[i * 4] = rgb >> 16;
    pixels.data[i * 4 + 1] = (rgb >> 8) & 255;
    pixels.data[i * 4 + 2] = rgb & 255;
    pixels.data[i * 4 + 3] = 255;
  }
  smallCtx.putImageData(pixels, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(small, left, top, pattern.width * cell, pattern.height * cell);
  small.width = small.height = 0;
  if (codes) for (let y = 0; y < pattern.height; y++)
    for (let x = 0; x < pattern.width; x++) {
      const color = colors[pattern.cells[y * pattern.width + x]!];
      const px = left + x * cell,
        py = top + y * cell;
      if (codes && color) {
        const rgb = parseInt(color.hex.slice(1), 16),
          luminance =
            ((rgb >> 16) * 299 + ((rgb >> 8) & 255) * 587 + (rgb & 255) * 114) /
            1000;
        ctx.fillStyle = luminance > 145 ? "#16202b" : "#ffffff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        let fontSize = Math.max(7, Math.floor(cell * 0.48));
        ctx.font = `600 ${fontSize}px sans-serif`;
        while (fontSize > 6 && ctx.measureText(color.code).width > cell - 2) {
          fontSize--;
          ctx.font = `600 ${fontSize}px sans-serif`;
        }
        ctx.fillText(color.code, px + cell / 2, py + cell / 2, cell - 1);
      }
    }
  ctx.textBaseline = "alphabetic";
  for (let x = 0; x <= pattern.width; x++) {
    ctx.strokeStyle = x % 5 === 0 ? "#34425688" : "#34425630";
    ctx.lineWidth = x % 5 === 0 ? 1 : 0.5;
    ctx.beginPath();
    ctx.moveTo(left + x * cell + 0.5, top);
    ctx.lineTo(left + x * cell + 0.5, top + pattern.height * cell);
    ctx.stroke();
  }
  for (let y = 0; y <= pattern.height; y++) {
    ctx.strokeStyle = y % 5 === 0 ? "#34425688" : "#34425630";
    ctx.lineWidth = y % 5 === 0 ? 1 : 0.5;
    ctx.beginPath();
    ctx.moveTo(left, top + y * cell + 0.5);
    ctx.lineTo(left + pattern.width * cell, top + y * cell + 0.5);
    ctx.stroke();
  }
  if (coordinates) {
    ctx.fillStyle = "#445064";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    for (let x = 0; x < pattern.width; x++)
      if (x === 0 || (x + 1) % 5 === 0)
        ctx.fillText(String(x + 1), left + (x + 0.5) * cell, top - 8);
    ctx.textAlign = "right";
    for (let y = 0; y < pattern.height; y++)
      if (y === 0 || (y + 1) % 5 === 0)
        ctx.fillText(String(y + 1), left - 8, top + (y + 0.65) * cell);
  }
}

export function thumbnail(
  pattern: BeadPattern,
  colors: BeadColor[],
): string | null {
  const canvas = document.createElement("canvas");
  try {
    paintGrid(
      canvas,
      pattern,
      colors,
      Math.min(4, 256 / Math.max(pattern.width, pattern.height)),
    );
    return canvas.toDataURL("image/png");
  } catch {
    return null;
  } finally {
    canvas.width = canvas.height = 0;
  }
}

export function safeName(name: string): string {
  return (
    name
      .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
      .slice(0, 80)
      .trim() || "拼豆图纸"
  );
}
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  // 下载开始后再释放，兼容下载任务异步消费 Blob URL 的浏览器。
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
export async function downloadPng(project: BeadPatternProject): Promise<void> {
  const canvas = document.createElement("canvas"),
    pattern = project.pattern;
  const cell = Math.min(
    20,
    Math.floor((4096 - 62) / pattern.width),
    Math.floor((4096 - 100) / pattern.height),
  );
  try {
    paintGrid(
      canvas,
      pattern,
      getPalette(project.paletteId).colors,
      cell,
      true,
      true,
      project.name,
    );
    if (
      canvas.width > 4096 ||
      canvas.height > 4096 ||
      canvas.width * canvas.height > 16_000_000
    )
      throw new Error("导出图纸超过画布上限，请减小规格");
    const blob = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (value) =>
          value ? resolve(value) : reject(new Error("图纸编码失败，请重试")),
        "image/png",
      ),
    );
    downloadBlob(blob, `${safeName(project.name)}.png`);
  } finally {
    canvas.width = canvas.height = 0;
  }
}
export function materialCsv(project: BeadPatternProject): string {
  const palette = getPalette(project.paletteId),
    rows = usageOf(project.pattern, palette.colors);
  const quote = (value: string | number) =>
    `"${String(value).replace(/"/g, '""')}"`;
  return (
    "\ufeff" +
    [
      ["品牌", "色号", "HEX", "数量"],
      ...rows.map((row) => [palette.name, row.code, row.hex, row.count]),
      ["合计", "", "", rows.reduce((sum, row) => sum + row.count, 0)],
    ]
      .map((row) => row.map(quote).join(","))
      .join("\r\n")
  );
}
export function materialText(project: BeadPatternProject): string {
  const palette = getPalette(project.paletteId),
    rows = usageOf(project.pattern, palette.colors);
  return (
    `${project.name} · ${palette.name}\n${project.pattern.width} × ${project.pattern.height} 格\n` +
    rows.map((row) => `${row.code} × ${row.count} 颗`).join("\n") +
    `\n合计 ${rows.reduce((n, row) => n + row.count, 0)} 颗`
  );
}
export function downloadCsv(project: BeadPatternProject): void {
  downloadBlob(
    new Blob([materialCsv(project)], { type: "text/csv;charset=utf-8" }),
    `${safeName(project.name)}-备料清单.csv`,
  );
}
export function downloadProject(project: BeadPatternProject): void {
  downloadBlob(
    new Blob([projectJson(project)], { type: "application/json" }),
    `${safeName(project.name)}.beads.json`,
  );
}
