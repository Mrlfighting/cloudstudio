/** 独立 IndexedDB v2：兼容旧草稿，增加工作区与按目标账号隔离的迁移关系。 */
import type { BeadDraft, BeadWorkspace, MigrationRecord } from "./types.ts";
import { parseProject, validParams } from "./project.ts";
import { getPalette } from "./palettes.ts";
import { assertLease, lease, waitForOwner } from "./session.ts";

let opening: Promise<IDBDatabase> | null = null;
function database(): Promise<IDBDatabase> {
  if (!opening)
    opening = new Promise<IDBDatabase>((resolve, reject) => {
      if (typeof indexedDB === "undefined") {
        reject(new Error("浏览器不支持本地草稿，请导出项目备份"));
        return;
      }
      const request = indexedDB.open("cloudatelier-bead-patterns", 2);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("drafts"))
          db.createObjectStore("drafts", { keyPath: "id" }).createIndex(
            "owner",
            "owner",
          );
        // 在升级事务中补齐旧创建时间；这是兼容值，不是原始历史创建时间。
        const cursor = request.transaction!.objectStore("drafts").openCursor();
        cursor.onsuccess = () => {
          const c = cursor.result;
          if (c) {
            c.update({
              ...c.value,
              createdAt:
                c.value.createdAt ??
                c.value.project?.updatedAt ??
                new Date().toISOString(),
            });
            c.continue();
          }
        };
        if (!db.objectStoreNames.contains("workspaces"))
          db.createObjectStore("workspaces", { keyPath: "owner" });
        if (!db.objectStoreNames.contains("migrations"))
          db.createObjectStore("migrations", { keyPath: "key" }).createIndex(
            "owner",
            "owner",
          );
      };
      request.onsuccess = () => {
        const db = request.result;
        db.onversionchange = () => {
          db.close();
          opening = null;
        };
        resolve(db);
      };
      request.onerror = () =>
        reject(new Error("本地存储不可用，请导出项目备份"));
      request.onblocked = () =>
        reject(new Error("请关闭其他旧版拼豆页面后重试"));
    }).catch((error) => {
      opening = null;
      throw error;
    });
  return opening;
}
async function transaction<T>(
  store: string,
  mode: IDBTransactionMode,
  action: (store: IDBObjectStore) => IDBRequest<T>,
  guard?: () => void,
): Promise<T> {
  const db = await database();
  guard?.();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, mode);
    let req: IDBRequest<T>;
    try {
      req = action(tx.objectStore(store));
    } catch {
      tx.abort();
      reject(new Error("本地存储失败或空间不足，请下载项目备份"));
      return;
    }
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
  await waitForOwner(owner);
  const rows = (await transaction("drafts", "readonly", (s) =>
    s.index("owner").getAll(owner),
  )) as BeadDraft[];
  return rows
    .filter((row) => {
      try {
        parseProject(row.project);
        return row.owner === owner;
      } catch {
        return false;
      }
    })
    .sort((a, b) => b.project.updatedAt.localeCompare(a.project.updatedAt));
}
export async function saveDraft(draft: BeadDraft): Promise<void> {
  const token = lease(draft.owner);
  await waitForOwner(draft.owner);
  const project = parseProject(draft.project);
  await transaction(
    "drafts",
    "readwrite",
    (s) =>
      s.put({
        ...draft,
        project,
        createdAt: draft.createdAt ?? project.updatedAt,
      }),
    () => assertLease(draft.owner, token),
  );
}
export async function deleteDraft(id: string, owner: string): Promise<void> {
  const token = lease(owner);
  await waitForOwner(owner);
  const db = await database();
  assertLease(owner, token);
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction("drafts", "readwrite"),
      store = tx.objectStore("drafts"),
      req = store.get(id);
    req.onsuccess = () => {
      if (req.result?.owner === owner) store.delete(id);
    };
    tx.oncomplete = () => resolve();
    tx.onerror = tx.onabort = () => reject(new Error("删除本地草稿失败"));
  });
}
export async function saveWorkspace(workspace: BeadWorkspace): Promise<void> {
  const token = lease(workspace.owner);
  await waitForOwner(workspace.owner);
  await transaction(
    "workspaces",
    "readwrite",
    (s) => s.put(workspace),
    () => assertLease(workspace.owner, token),
  );
}
export async function loadWorkspace(
  owner: string,
): Promise<BeadWorkspace | null> {
  await waitForOwner(owner);
  const row = (await transaction("workspaces", "readonly", (s) =>
    s.get(owner),
  )) as BeadWorkspace | undefined;
  if (!row) return null;
  if (row.owner !== owner || !validParams(row.params))
    throw new Error("本地工作区参数损坏，请从草稿箱恢复");
  getPalette(row.paletteId);
  if (row.project) row.project = parseProject(row.project);
  return row;
}
export async function saveMigration(record: MigrationRecord): Promise<void> {
  const token = lease(record.owner);
  await waitForOwner(record.owner);
  await transaction(
    "migrations",
    "readwrite",
    (s) => s.put(record),
    () => assertLease(record.owner, token),
  );
}
export async function getMigration(
  owner: string,
  sourceId: string,
): Promise<MigrationRecord | undefined> {
  await waitForOwner(owner);
  return transaction("migrations", "readonly", (s) =>
    s.get(`${owner}/${sourceId}`),
  );
}
export async function clearOwner(owner: string): Promise<void> {
  const db = await database();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(
      ["drafts", "workspaces", "migrations"],
      "readwrite",
    );
    tx.objectStore("workspaces").delete(owner);
    for (const name of ["drafts", "migrations"]) {
      const req = tx
        .objectStore(name)
        .index("owner")
        .openCursor(IDBKeyRange.only(owner));
      req.onsuccess = () => {
        const c = req.result;
        if (c) {
          c.delete();
          c.continue();
        }
      };
    }
    tx.oncomplete = () => resolve();
    tx.onerror = tx.onabort = () =>
      reject(new Error("账号本地数据清理失败，请重试"));
  });
}
