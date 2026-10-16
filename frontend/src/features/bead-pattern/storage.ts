/** 独立 IndexedDB，不复用网站其他存储；每个账号与游客按命名空间隔离。 */
import type { BeadDraft } from "./types.ts";
import { parseProject } from "./project.ts";

let opening: Promise<IDBDatabase> | null = null;
function database(): Promise<IDBDatabase> {
  if (!opening)
    opening = new Promise<IDBDatabase>((resolve, reject) => {
      if (typeof indexedDB === "undefined") {
        reject(new Error("浏览器不支持本地草稿，请导出项目备份"));
        return;
      }
      const request = indexedDB.open("cloudatelier-bead-patterns", 1);
      request.onupgradeneeded = () => {
        const store = request.result.createObjectStore("drafts", {
          keyPath: "id",
        });
        store.createIndex("owner", "owner");
      };
      request.onsuccess = () => {
        request.result.onversionchange = () => {
          request.result.close();
          opening = null;
        };
        resolve(request.result);
      };
      request.onerror = () =>
        reject(new Error("本地存储不可用，请导出项目备份"));
      request.onblocked = () =>
        reject(new Error("请关闭其他拼豆页面后重试本地保存"));
    }).catch((error) => {
      opening = null;
      throw error;
    });
  return opening;
}

/** 写操作等事务完成后才提示成功，避免只等 request 成功漏报磁盘配额错误。 */
async function transaction<T>(
  mode: IDBTransactionMode,
  action: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("drafts", mode),
      req = action(tx.objectStore("drafts"));
    let result: T;
    req.onsuccess = () => {
      result = req.result;
    };
    tx.oncomplete = () => resolve(result);
    tx.onerror = tx.onabort = () =>
      reject(new Error("本地存储失败或空间不足，请下载项目备份"));
  });
}

export async function listDrafts(owner: string): Promise<BeadDraft[]> {
  const rows = (await transaction("readonly", (store) =>
    store.index("owner").getAll(owner),
  )) as BeadDraft[];
  // 损坏的单条草稿不阻断整个工具；恢复时还会再次验证协议。
  return rows
    .filter((row) => {
      try {
        parseProject(row.project);
        return true;
      } catch {
        return false;
      }
    })
    .sort((a, b) => b.project.updatedAt.localeCompare(a.project.updatedAt));
}
export async function saveDraft(draft: BeadDraft): Promise<void> {
  await transaction("readwrite", (store) =>
    store.put({ ...draft, project: parseProject(draft.project) }),
  );
}
export async function deleteDraft(id: string, owner: string): Promise<void> {
  const existing = (await transaction("readonly", (store) => store.get(id))) as
    | BeadDraft
    | undefined;
  if (existing?.owner === owner)
    await transaction("readwrite", (store) => store.delete(id));
}
