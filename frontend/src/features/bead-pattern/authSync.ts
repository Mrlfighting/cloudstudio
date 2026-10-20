/** 拼豆专用跨标签页会话通知；消息只触发重新核验，绝不当作登录凭据。 */
import { watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { beadStorageNotice, invalidate, beadOwner } from "./session.ts";

const KEY = "cloudatelier:beads:session:v1";
const EVENT = "cloudatelier:beads:session-changed";
interface Notice {
  owner: string;
  nonce: string;
}
function storedNotice(): Notice | null {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) ?? "null");
    return value &&
      typeof value.nonce === "string" &&
      /^(guest|user:\d+)$/.test(value.owner)
      ? value
      : null;
  } catch {
    return null;
  }
}
export function notifyBeadSessionChanged(): void {
  window.dispatchEvent(new Event(EVENT));
}
/** 即使 storage/BroadcastChannel 事件尚未派发，也能阻止旧标签页先发请求。 */
export function beadSessionStamp(): string | undefined {
  return storedNotice()?.nonce;
}
export function assertSharedBeadOwner(owner: string, stamp?: string): void {
  const notice = storedNotice();
  if (
    notice &&
    (notice.owner !== owner || (stamp !== undefined && notice.nonce !== stamp))
  ) {
    notifyBeadSessionChanged();
    throw new DOMException(
      "登录账号已在其他页面变更，本次操作已取消",
      "AbortError",
    );
  }
}
export function startBeadAuthSync(): () => void {
  const auth = useAuthStore();
  const owner = () => (auth.user ? `user:${auth.user.id}` : "guest");
  let muted = false,
    disposed = false,
    serial = 0;
  let request: AbortController | undefined;
  let seen = storedNotice()?.nonce;
  let channel: BroadcastChannel | undefined;
  try {
    channel = new BroadcastChannel(KEY);
  } catch {
    /* 后端前置条件仍负责最终隔离。 */
  }
  function locally(action: () => void) {
    muted = true;
    try {
      action();
    } finally {
      muted = false;
    }
  }
  function publish() {
    const notice: Notice = { owner: owner(), nonce: crypto.randomUUID() };
    seen = notice.nonce;
    try {
      localStorage.setItem(KEY, JSON.stringify(notice));
    } catch {
      /* 继续使用广播。 */
    }
    channel?.postMessage(notice);
  }
  function clearPrivateView() {
    // 即使 A→B→A 被合并到一次消息，也撤销旧代次，不能接收旧响应。
    invalidate(beadOwner.value);
    locally(() => auth.reset());
  }
  async function reconcile(clear = false) {
    const current = ++serial;
    request?.abort();
    request = new AbortController();
    const before = storedNotice()?.nonce;
    if (clear) clearPrivateView();
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE ?? "/api/v1"}/users/me`,
        {
          credentials: "include",
          cache: "no-store",
          signal: request.signal,
        },
      );
      if (response.status !== 401 && !response.ok)
        throw new Error("登录状态暂时无法核验");
      const user = response.ok ? await response.json() : null;
      if (
        user &&
        (!Number.isSafeInteger(user.id) ||
          user.id < 1 ||
          typeof user.username !== "string")
      )
        throw new Error("登录状态响应无效");
      if (disposed || current !== serial) return;
      if (storedNotice()?.nonce !== before) {
        void reconcile(true);
        return;
      }
      const actual = user ? `user:${user.id}` : "guest";
      if (actual !== owner()) {
        clearPrivateView();
        locally(() => {
          if (user) auth.setUser(user);
        });
      }
      // 旧通知可能来自已关闭页面；最终以真实会话为准修正，不信任消息中的账号。
      if (storedNotice()?.owner !== actual) publish();
    } catch (error) {
      if (
        !disposed &&
        current === serial &&
        !(error instanceof DOMException && error.name === "AbortError")
      ) {
        clearPrivateView();
        beadStorageNotice.value =
          "登录状态核验失败，已清除旧账号视图；请重新登录后重试。";
      }
    }
  }
  function receive(value: Notice | null) {
    if (!value || typeof value.nonce !== "string" || value.nonce === seen)
      return;
    seen = value.nonce;
    beadStorageNotice.value = "登录状态已在其他页面变更，旧账号操作已取消。";
    void reconcile(true);
  }
  const stop = watch(
    () => auth.user?.id,
    () => {
      if (muted || !auth.initialized) return;
      ++serial;
      request?.abort();
      publish();
    },
    { flush: "sync" },
  );
  const storage = (event: StorageEvent) => {
    if (event.key === KEY) receive(storedNotice());
  };
  const changed = () => {
    void reconcile(true);
  };
  const focus = () => {
    if (document.visibilityState === "visible") void reconcile();
  };
  channel?.addEventListener("message", (event) => receive(event.data));
  window.addEventListener("storage", storage);
  window.addEventListener(EVENT, changed);
  window.addEventListener("focus", focus);
  document.addEventListener("visibilitychange", focus);
  // 首次进入时处理已存在的其他标签页通知，但不把一次页面加载广播为退出。
  if (auth.initialized && storedNotice() && storedNotice()!.owner !== owner())
    void reconcile(true);
  return () => {
    disposed = true;
    ++serial;
    request?.abort();
    stop();
    channel?.close();
    window.removeEventListener("storage", storage);
    window.removeEventListener(EVENT, changed);
    window.removeEventListener("focus", focus);
    document.removeEventListener("visibilitychange", focus);
  };
}
