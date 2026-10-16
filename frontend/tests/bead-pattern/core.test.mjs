/** 使用 Node 原生测试验证实际算法和项目协议，不引入额外测试框架。 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import {
  deltaE,
  gridSize,
  mapPattern,
  limitColors,
  cleanSpeckles,
  usageOf,
} from "../../src/features/bead-pattern/core.ts";
import {
  DEFAULT_PARAMS,
  ENGINE_VERSION,
  PALETTE_REVISION,
} from "../../src/features/bead-pattern/types.ts";
import {
  PALETTES,
  usableColors,
} from "../../src/features/bead-pattern/palettes.ts";
import {
  parseProject,
  projectJson,
} from "../../src/features/bead-pattern/project.ts";
import { materialCsv } from "../../src/features/bead-pattern/export.ts";
import { inspectFile } from "../../src/features/bead-pattern/image.ts";

const colors = [
  { code: "W", hex: "#FFFFFF" },
  { code: "B", hex: "#000000" },
  { code: "R", hex: "#FF0000" },
  { code: "G", hex: "#00FF00" },
];
const params = { ...DEFAULT_PARAMS, maxColors: 4 };
const rgba = (cells) =>
  Uint8ClampedArray.from(
    cells.flatMap((i) =>
      i < 0
        ? [255, 0, 0, 0]
        : [
            ...colors[i].hex
              .slice(1)
              .match(/../g)
              .map((s) => parseInt(s, 16)),
            255,
          ],
    ),
  );
function project() {
  return {
    format: "cloudatelier-bead-pattern",
    version: 1,
    engineVersion: ENGINE_VERSION,
    paletteRevision: PALETTE_REVISION,
    paletteId: PALETTES[0].id,
    name: "测试图纸",
    updatedAt: "2026-10-16T00:00:00Z",
    params,
    pattern: { width: 2, height: 2, cells: [0, 1, -1, 0] },
  };
}

test("CIEDE2000 符合 Sharma 标准样例，而非 RGB 欧氏距离", () => {
  for (const [a, b, expected] of [
    [[50, 2.6772, -79.7751], [50, 0, -82.7485], 2.0425],
    [[50, 3.1571, -77.2803], [50, 0, -82.7485], 2.8615],
    [[50, 2.8361, -74.02], [50, 0, -82.7485], 3.4412],
  ]) {
    const lab = ([l, a, b]) => ({ mode: "lab65", l, a, b });
    assert.ok(Math.abs(deltaE(lab(a), lab(b)) - expected) < 0.0001);
    assert.equal(deltaE(lab(a), lab(a)), 0);
  }
});
test("横图、竖图和极端比例均保持比例并限制最长边", () => {
  assert.deepEqual(gridSize(1000, 500, 100), { width: 100, height: 50 });
  assert.deepEqual(gridSize(100, 400, 200), { width: 50, height: 200 });
  assert.deepEqual(gridSize(1, 10000, 200), { width: 1, height: 200 });
  assert.throws(() => gridSize(0, 100, 100));
});
test("五套色卡来源哈希和可用色数固定", () => {
  assert.deepEqual(
    PALETTES.map((p) => p.colors.length),
    [291, 289, 277, 285, 286],
  );
  const base = new URL(
    "../../src/features/bead-pattern/palettes/",
    import.meta.url,
  );
  const manifest = JSON.parse(
    readFileSync(new URL("sources.json", base), "utf8"),
  );
  for (const [file, hash] of Object.entries(manifest.files))
    assert.equal(
      createHash("sha256")
        .update(readFileSync(new URL(file, base)))
        .digest("hex"),
      hash,
    );
});
test("未知色号、透明色与重复 HEX 不参与匹配", () => {
  assert.equal(
    usableColors([
      { code: "?", hex: "#FFFFFF" },
      { code: "A", hex: "#ffffff" },
      { code: "B", hex: "#FFFFFF" },
      { code: "C", hex: "#FF000080" },
    ]).length,
    1,
  );
});
test("透明格不匹配、不计数，真实品牌色保持色号", () => {
  const result = mapPattern(rgba([0, 1, 2, -1]), 2, 2, colors, params);
  assert.deepEqual(result.pattern.cells, [0, 1, 2, -1]);
  assert.equal(
    usageOf(result.pattern, colors).reduce((n, r) => n + r.count, 0),
    3,
  );
});
test("限色硬上限在高反差颜色下也成立，且保留空格", () => {
  const cells = limitColors([0, 1, 2, 3, 3, -1], colors, 2);
  assert.ok(new Set(cells.filter((c) => c >= 0)).size <= 2);
  assert.equal(cells[5], -1);
  assert.deepEqual(cells, limitColors([0, 1, 2, 3, 3, -1], colors, 2));
});
test("边界洪泛保留被前景包围的同色孔洞", () => {
  const cells = Array.from({ length: 49 }, (_, i) =>
    i < 7 || i >= 42 || i % 7 === 0 || i % 7 === 6 || i === 24 ? 0 : 1,
  );
  const result = mapPattern(rgba(cells), 7, 7, colors, {
    ...params,
    removeBackground: true,
  });
  assert.equal(result.pattern.cells[0], -1);
  assert.equal(result.pattern.cells[24], 0);
  assert.equal(
    usageOf(result.pattern, colors).reduce((n, r) => n + r.count, 0),
    25,
  );
});
test("自动背景无共识时保留图片，手动背景可以继续处理", () => {
  const auto = mapPattern(rgba([0, 1, 2, 3]), 2, 2, colors, {
    ...params,
    removeBackground: true,
  });
  assert.equal(auto.warnings.length, 1);
  assert.equal(auto.pattern.cells.filter((c) => c >= 0).length, 4);
  const manual = mapPattern(rgba([0, 1, 2, 3]), 2, 2, colors, {
    ...params,
    removeBackground: true,
    backgroundColor: "#FFFFFF",
  });
  assert.equal(manual.pattern.cells[0], -1);
});
test("孤立杂点清理不填充透明格、不改变总用豆数", () => {
  const cells = Array(25).fill(1);
  cells[12] = 0;
  cells[0] = -1;
  const cleaned = cleanSpeckles({ width: 5, height: 5, cells }, colors, 1);
  assert.equal(cleaned[12], 1);
  assert.equal(cleaned[0], -1);
  assert.equal(cleaned.filter((c) => c >= 0).length, 24);
});
test("项目往返保持网格并剥离附加字段，CSV 总数与网格一致", () => {
  const value = project(),
    parsed = parseProject({
      ...value,
      sourceUrl: "sensitive",
      token: "not-exported",
    });
  assert.deepEqual(parseProject(JSON.parse(projectJson(parsed))), value);
  assert.ok(!projectJson(parsed).includes("sourceUrl"));
  assert.ok(materialCsv(value).includes('"合计","","","3"'));
  assert.throws(() => parseProject({ ...value, version: 9 }));
  assert.throws(() =>
    parseProject({ ...value, pattern: { width: 1, height: 1, cells: [999] } }),
  );
  assert.throws(() =>
    parseProject({ ...value, params: { ...params, maxColors: 0 } }),
  );
});
test("输入预检查拒绝伪装类型、超大文件和超像素图片", async () => {
  await assert.rejects(
    inspectFile(new Blob(["not an image"], { type: "image/png" })),
  );
  await assert.rejects(
    inspectFile(new Blob([new Uint8Array(10 * 1024 * 1024 + 1)])),
  );
  const data = new Uint8Array(24);
  data.set([137, 80, 78, 71], 0);
  const view = new DataView(data.buffer);
  view.setUint32(16, 10000);
  view.setUint32(20, 10000);
  await assert.rejects(inspectFile(new Blob([data])), /2500/);
});
