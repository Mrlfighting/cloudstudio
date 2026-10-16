/** 单任务 Worker；终止 Worker 即可立即取消 CPU 运算，无需跨域隔离头。 */
import pica from "pica";
import { gridSize, mapPattern } from "./core.ts";
import type { BeadColor, GenerationParams } from "./types.ts";

export interface WorkerInput {
  rgba: Uint8ClampedArray;
  width: number;
  height: number;
  colors: BeadColor[];
  params: GenerationParams;
}
self.onmessage = async (event: MessageEvent<WorkerInput>) => {
  try {
    const start = performance.now(),
      { rgba, width, height, colors, params } = event.data;
    const size = gridSize(width, height, params.longEdge);
    self.postMessage({ type: "progress", value: 5 });
    // Worker 内禁用额外线程池；整次任务只占用一个计算 Worker。
    const reduced = await pica({
      features: ["js", "wasm"],
      concurrency: 1,
    }).resizeBuffer({
      src: rgba,
      width,
      height,
      toWidth: size.width,
      toHeight: size.height,
      filter: "lanczos3",
    });
    const output = mapPattern(
      new Uint8ClampedArray(reduced),
      size.width,
      size.height,
      colors,
      params,
      (value) => self.postMessage({ type: "progress", value }),
    );
    self.postMessage({
      type: "done",
      output: { ...output, durationMs: performance.now() - start },
    });
  } catch (error) {
    self.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : "图纸生成失败",
    });
  }
};
