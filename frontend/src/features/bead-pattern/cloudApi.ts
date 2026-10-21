/** 拼豆专用传输：复用 Cookie/CSRF，禁止 401 自动登录后重放旧账号写入。 */
import axios from "axios";
import type { AxiosRequestConfig } from "axios";
import { getCookie, setCookie } from "@/utils/cookies";
import { useAuthStore } from "@/stores/auth";
import { useEmailVerificationStore } from "@/features/email-verification/store";
import {
  beadOwner,
  lease,
  assertLease,
  trackRequest,
  beadStorageNotice,
  transitionOwner,
} from "./session.ts";
import type {
  BeadPatternProject,
  CloudDetail,
  CloudItem,
  CloudLink,
} from "./types.ts";
import { projectJson } from "./project.ts";
import {
  assertSharedBeadOwner,
  beadSessionStamp,
  notifyBeadSessionChanged,
} from "./authSync.ts";
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "/api/v1",
  withCredentials: true,
  timeout: 30000,
});
export async function cloudRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const auth = useAuthStore();
  const account = auth.user?.id;
  const email = useEmailVerificationStore();
  // 仅扩展云端权限前置检查，原有账号代次、幂等与CSRF处理继续复用。
  await email.assertPrivateAccess();
  if (auth.user?.id !== account) throw new DOMException("账号已切换", "AbortError");
  const currentOwner = () => (auth.user ? `user:${auth.user.id}` : "guest");
  // 登录 Store 是唯一身份来源；首次加载/热更新时不能依赖监听组件已同步完成。
  const owner = currentOwner();
  transitionOwner(owner);
  const token = lease(owner);
  if (owner === "guest") throw new Error("请登录后再操作云端作品");
  const stamp = beadSessionStamp();
  assertSharedBeadOwner(owner, stamp);
  const controller = new AbortController(),
    release = trackRequest(owner, controller);
  const check = () => {
    if (!email.canUsePrivate) throw new DOMException("邮箱验证状态已变更", "AbortError");
    // 响应与 CSRF 重试同样检查真实登录态，避免辅助状态滞后时泄露旧账号结果。
    if (currentOwner() !== owner) {
      transitionOwner(currentOwner());
      throw new DOMException("账号已切换", "AbortError");
    }
    assertLease(owner, token);
    if (beadOwner.value !== owner)
      throw new DOMException("账号已切换", "AbortError");
    assertSharedBeadOwner(owner, stamp);
  };
  async function send(retry = false): Promise<T> {
    check();
    try {
      const res = await client.request<T>({
        ...config,
        signal: controller.signal,
        headers: {
          ...config.headers,
          "X-CSRF-Token": getCookie("csrf_token") ?? "",
          "X-Bead-Owner": owner.slice(5),
        },
      });
      check();
      return res.data;
    } catch (error) {
      check();
      if (axios.isAxiosError(error)) {
        if (error.response?.headers["x-bead-session-changed"]) {
          beadStorageNotice.value =
            "登录账号已在其他页面变更，本次操作已取消。";
          notifyBeadSessionChanged();
          throw new DOMException("账号已切换，本次操作已取消", "AbortError");
        }
        if (error.response?.status === 401) {
          beadStorageNotice.value = "登录已失效，请重新登录后再次保存。";
          auth.reset();
          throw new Error("登录已失效；重新登录后请再次保存");
        }
        if (
          !retry &&
          error.response?.status === 403 &&
          error.response.headers["x-csrf-error"]
        ) {
          let refreshed;
          try {
            refreshed = await client.post("/auth/refresh-csrf", null, {
              signal: controller.signal,
            });
          } catch (refreshError) {
            check();
            if (
              axios.isAxiosError(refreshError) &&
              refreshError.response?.status === 401
            ) {
              beadStorageNotice.value = "登录已失效，请重新登录后再次保存。";
              auth.reset();
            }
            throw refreshError;
          }
          check();
          setCookie("csrf_token", refreshed.data.csrf_token);
          return send(true);
        }
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") error.message = detail;
      }
      throw error;
    }
  }
  try {
    return await send();
  } finally {
    release();
  }
}
export function listCloud(page = 1, keyword = "") {
  return cloudRequest<{ data: CloudItem[]; total_count: number }>({
    url: "/bead-patterns/",
    params: { page, keyword },
  });
}
export function getCloud(id: string) {
  return cloudRequest<CloudDetail>({ url: `/bead-patterns/${id}` });
}
export function cloudSource(id: string) {
  return cloudRequest<Blob>({
    url: `/bead-patterns/${id}/source`,
    responseType: "blob",
  });
}
export function cloudLink(item: CloudItem): CloudLink {
  return { id: item.id, revision: item.revision, clientId: item.client_id };
}
export function putCloud(
  project: BeadPatternProject,
  source: Blob | null,
  preview: string | null,
  clientId: string,
  link?: CloudLink,
) {
  const form = new FormData();
  form.set("project", projectJson(project));
  if (link) form.set("revision", String(link.revision));
  else form.set("client_id", clientId);
  if (source) form.set("source", source, "工作源.png");
  if (preview) {
    const raw = atob(preview.split(",")[1]!);
    const bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    form.set(
      "thumbnail",
      new Blob([bytes], { type: "image/png" }),
      "缩略图.png",
    );
  }
  return cloudRequest<CloudDetail>({
    url: link ? `/bead-patterns/${link.id}` : "/bead-patterns/",
    method: link ? "put" : "post",
    data: form,
  });
}
export function renameCloud(item: CloudItem, name: string) {
  return cloudRequest<CloudDetail>({
    url: `/bead-patterns/${item.id}`,
    method: "patch",
    data: { name, revision: item.revision },
  });
}
export function deleteCloud(item: CloudItem) {
  return cloudRequest({
    url: `/bead-patterns/${item.id}`,
    method: "delete",
    params: { revision: item.revision },
  });
}
