/** 轻量账号边界；全站监听不引入算法/画布，异步操作均核对租约。 */
import { ref } from "vue";
export const beadOwner = ref("guest");
export const beadStorageNotice = ref("");
const generations = new Map<string, number>();
const barriers = new Map<string, Promise<void>>();
const requests = new Map<string, Set<AbortController>>();
export function trackRequest(
  owner: string,
  controller: AbortController,
): () => void {
  if (!requests.has(owner)) requests.set(owner, new Set());
  requests.get(owner)!.add(controller);
  return () => requests.get(owner)?.delete(controller);
}
export function lease(owner: string): number {
  return generations.get(owner) ?? 0;
}
export function invalidate(owner: string): void {
  generations.set(owner, lease(owner) + 1);
  for (const controller of requests.get(owner) ?? []) controller.abort();
  requests.delete(owner);
}
export function validLease(owner: string, token: number): boolean {
  return lease(owner) === token;
}
export function assertLease(owner: string, token: number): void {
  if (!validLease(owner, token))
    throw new DOMException("账号已切换，旧任务已取消", "AbortError");
}
export function waitForOwner(owner: string): Promise<void> {
  return barriers.get(owner) ?? Promise.resolve();
}
export function keepLocal(owner: string): boolean {
  try {
    return localStorage.getItem(`beads:keep:${owner}`) !== "false";
  } catch {
    return true;
  }
}
export function setKeepLocal(owner: string, keep: boolean): void {
  localStorage.setItem(`beads:keep:${owner}`, String(keep));
}
export function transitionOwner(next: string): void {
  const previous = beadOwner.value;
  if (previous === next) return;
  invalidate(previous);
  // 先登记清理屏障；快速重登不能早于旧账号清理完成而恢复数据。
  if (previous !== "guest" && !keepLocal(previous)) queueCleanup(previous);
  // 上次关闭浏览器前若清理失败，下次登录先重试，不能直接恢复待清理数据。
  try {
    if (next !== "guest" && localStorage.getItem(`beads:purge:${next}`))
      queueCleanup(next);
  } catch {
    /* 存储不可用时由工作区报告。 */
  }
  beadOwner.value = next;
}
function queueCleanup(owner: string): void {
  try {
    localStorage.setItem(`beads:purge:${owner}`, "pending");
  } catch {
    /* 数据库清理仍然继续。 */
  }
  const cleanup = waitForOwner(owner)
    .catch(() => {})
    .then(async () => {
      const { clearOwner } = await import("./storage.ts");
      await clearOwner(owner);
      if (barriers.get(owner) === cleanup) {
        try {
          localStorage.removeItem(`beads:purge:${owner}`);
        } catch {
          /* 下次可重复清理。 */
        }
      }
    });
  barriers.set(owner, cleanup);
  void cleanup.catch(() => {
    beadStorageNotice.value =
      "本地拼豆数据清理失败，下次登录将重试；请检查浏览器存储权限。";
  });
}
