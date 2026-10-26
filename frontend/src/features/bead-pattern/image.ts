/** 图片准备只保留最长边 1600px 的 PNG 工作源，原始位图及时释放。 */
import pica from "pica";
import { MAX_FILE_BYTES, MAX_SOURCE_PIXELS } from "./types.ts";

const resizer = pica({
  concurrency: 1,
  features: ["js", "wasm", "ww"],
  idle: 1000,
});

/** 先检查文件签名和尺寸，避免小体积超大图片在解码时分配巨量内存。 */
export async function inspectFile(
  file: Blob,
): Promise<{ width: number; height: number; animated: boolean }> {
  if (!file.size || file.size > MAX_FILE_BYTES)
    throw new Error("图片必须非空且不超过 10MB");
  const bytes = new Uint8Array(await file.arrayBuffer()),
    view = new DataView(bytes.buffer);
  const text = (start: number, end: number) =>
    String.fromCharCode(...bytes.slice(start, end));
  let width = 0,
    height = 0,
    animated = false;
  if (bytes.length >= 24 && text(1, 4) === "PNG" && bytes[0] === 137) {
    width = view.getUint32(16);
    height = view.getUint32(20);
  } else if (bytes.length >= 10 && /^GIF8[79]a$/.test(text(0, 6))) {
    width = view.getUint16(6, true);
    height = view.getUint16(8, true);
    animated = true;
  } else if (
    bytes.length >= 30 &&
    text(0, 4) === "RIFF" &&
    text(8, 12) === "WEBP"
  ) {
    const kind = text(12, 16);
    if (kind === "VP8X") {
      width = 1 + bytes[24]! + bytes[25]! * 256 + bytes[26]! * 65536;
      height = 1 + bytes[27]! + bytes[28]! * 256 + bytes[29]! * 65536;
      animated = !!(bytes[20]! & 2);
    } else if (
      kind === "VP8 " &&
      bytes[23] === 157 &&
      bytes[24] === 1 &&
      bytes[25] === 42
    ) {
      width = view.getUint16(26, true) & 0x3fff;
      height = view.getUint16(28, true) & 0x3fff;
    } else if (kind === "VP8L" && bytes[20] === 47) {
      const bits = view.getUint32(21, true);
      width = (bits & 0x3fff) + 1;
      height = ((bits >>> 14) & 0x3fff) + 1;
    }
  } else if (bytes[0] === 255 && bytes[1] === 216) {
    let offset = 2;
    while (offset + 8 < bytes.length) {
      if (bytes[offset] !== 255) break;
      while (bytes[offset] === 255) offset++;
      const marker = bytes[offset++]!;
      if (marker === 217 || marker === 218) break;
      if (marker === 1 || (marker >= 208 && marker <= 215)) continue;
      if (offset + 2 > bytes.length) break;
      const length = view.getUint16(offset);
      if (length < 2 || offset + length > bytes.length) break;
      if (
        [
          192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 205, 206, 207,
        ].includes(marker)
      ) {
        height = view.getUint16(offset + 3);
        width = view.getUint16(offset + 5);
        break;
      }
      offset += length;
    }
  }
  if (!width || !height)
    throw new Error("无法识别图片，请使用有效的 JPEG、PNG、WebP 或 GIF");
  if (width * height > MAX_SOURCE_PIXELS)
    throw new Error("图片超过 2500 万像素，请先缩小");
  return { width, height, animated };
}

export async function prepareSource(
  file: Blob,
): Promise<{ blob: Blob; animated: boolean }> {
  const meta = await inspectFile(file);
  const bitmap = await createImageBitmap(file, {
    imageOrientation: "from-image",
  });
  const canvas = document.createElement("canvas");
  try {
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    await resizer.resize(bitmap, canvas, { filter: "lanczos3" });
    return {
      blob: await resizer.toBlob(canvas, "image/png"),
      animated: meta.animated,
    };
  } finally {
    bitmap.close();
    canvas.width = canvas.height = 0;
  }
}

/** 生成前仅解码已缩小的工作源，传输后不在主线程保留 RGBA 副本。 */
export async function sourcePixels(
  blob: Blob,
): Promise<{ rgba: Uint8ClampedArray; width: number; height: number }> {
  const bitmap = await createImageBitmap(blob),
    canvas = document.createElement("canvas");
  try {
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) throw new Error("当前浏览器无法创建画布");
    ctx.drawImage(bitmap, 0, 0);
    return {
      rgba: ctx.getImageData(0, 0, canvas.width, canvas.height).data,
      width: canvas.width,
      height: canvas.height,
    };
  } finally {
    bitmap.close();
    canvas.width = canvas.height = 0;
  }
}
