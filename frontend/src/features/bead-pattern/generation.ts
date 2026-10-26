/** 最新任务独占 Worker，取消、重新生成及页面销毁均释放线程。 */
import type { WorkerInput } from "./generate.worker.ts";
import type { GenerationOutput } from "./types.ts";

export function createGenerator() {
  let cancelActive: (() => void) | null = null;
  return {
    cancel() {
      cancelActive?.();
    },
    run(
      input: WorkerInput,
      progress: (value: number) => void,
    ): Promise<GenerationOutput> {
      cancelActive?.();
      if (typeof Worker === "undefined")
        return Promise.reject(
          new Error("当前浏览器不支持后台计算，请使用新版浏览器"),
        );
      return new Promise((resolve, reject) => {
        const worker = new Worker(
          new URL("./generate.worker.ts", import.meta.url),
          { type: "module" },
        );
        const close = () => {
          worker.terminate();
          if (cancelActive === cancel) cancelActive = null;
        };
        const cancel = () => {
          close();
          reject(new DOMException("生成已取消", "AbortError"));
        };
        cancelActive = cancel;
        worker.onmessage = (event) => {
          const data = event.data;
          if (data.type === "progress") progress(data.value);
          else {
            close();
            if (data.type === "done") resolve(data.output);
            else reject(new Error(data.message));
          }
        };
        worker.onerror = () => {
          close();
          reject(new Error("计算线程异常，请缩小规格后重试"));
        };
        worker.postMessage(input, [input.rgba.buffer]);
      });
    },
  };
}
