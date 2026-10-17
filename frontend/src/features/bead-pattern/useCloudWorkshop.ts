/** 云端作品/迁移编排独立于转换引擎，所有异步回写核对账号和当前图纸。 */
import { computed, ref, shallowRef, watch } from "vue";
import type { Ref, ShallowRef, ComputedRef } from "vue";
import axios from "axios";
import { ElMessage } from "element-plus";
import { beadMessageBox as ElMessageBox } from "./dialogs.ts";
import { useAuthGateStore } from "@/stores/authGate";
import {
  listCloud,
  getCloud,
  cloudSource,
  putCloud,
  renameCloud,
  deleteCloud,
  cloudLink,
} from "./cloudApi.ts";
import { listDrafts, getMigration, saveMigration } from "./storage.ts";
import {
  lease,
  assertLease,
  validLease,
  keepLocal,
  setKeepLocal,
} from "./session.ts";
import { parseProject } from "./project.ts";
import { thumbnail } from "./export.ts";
import { getPalette } from "./palettes.ts";
import type {
  BeadWorkspace,
  CloudItem,
  CloudLink,
  BeadDraft,
} from "./types.ts";

interface Port {
  owner: ComputedRef<string>;
  project: ShallowRef<BeadWorkspace["project"]>;
  cloud: ShallowRef<CloudLink | undefined>;
  cloudClientId: Ref<string>;
  changed: ComputedRef<boolean>;
  ready: Ref<boolean>;
  deferPrompt: ComputedRef<boolean>;
  readyWait(): Promise<void>;
  snapshot(): BeadWorkspace;
  apply(workspace: BeadWorkspace): Promise<void>;
  persist(): Promise<void>;
  confirmReplace(): Promise<boolean>;
  closeLocalLibrary(): void;
}
export function useCloudWorkshop(port: Port) {
  const cloudVisible = ref(false),
    cloudBusy = ref(false),
    cloudLoading = ref(false),
    cloudError = ref("");
  const cloudRows = shallowRef<CloudItem[]>([]),
    cloudPage = ref(1),
    cloudTotal = ref(0),
    cloudKeyword = ref("");
  const retainLocal = ref(true),
    migrationVisible = ref(false),
    migrationBusy = ref(false);
  const migrationRows = shallowRef<BeadDraft[]>([]),
    selectedMigrations = ref<string[]>([]);
  const migrationStatuses = ref<Record<string, string>>({});
  const migrationCompleted = ref(0),
    migrationTotal = ref(0),
    migrationSummary = ref("");
  const cloudConflict = ref(false);
  const signedIn = computed(() => port.owner.value !== "guest");
  let loginContinuation = false,
    loadSerial = 0;
  let pendingPrompt = "";
  const previewUrl = (row: CloudItem) =>
    `${import.meta.env.VITE_API_BASE ?? "/api/v1"}/bead-patterns/${row.id}/thumbnail?revision=${row.revision}`;
  function showError(error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    cloudConflict.value =
      axios.isAxiosError(error) && error.response?.status === 409;
    cloudError.value =
      error instanceof Error ? error.message : "云端操作失败，请重试";
    ElMessage.error(cloudError.value);
  }
  async function refreshCloud() {
    if (!signedIn.value) return;
    const owner = port.owner.value,
      token = lease(owner),
      serial = ++loadSerial;
    cloudLoading.value = true;
    cloudError.value = "";
    try {
      const result = await listCloud(cloudPage.value, cloudKeyword.value);
      assertLease(owner, token);
      if (serial === loadSerial && owner === port.owner.value) {
        cloudRows.value = result.data;
        cloudTotal.value = result.total_count;
      }
    } catch (error) {
      if (serial === loadSerial && owner === port.owner.value) showError(error);
    } finally {
      if (serial === loadSerial) cloudLoading.value = false;
    }
  }
  async function openLibrary() {
    if (
      !signedIn.value &&
      !(await useAuthGateStore().requireAuthentication({
        reason: "登录后访问自己的云端拼豆作品",
      }))
    )
      return;
    cloudVisible.value = true;
    await refreshCloud();
  }
  async function openCloud(row: Pick<CloudItem, "id">) {
    const owner = port.owner.value,
      token = lease(owner);
    if (!(await port.confirmReplace())) return;
    try {
      assertLease(owner, token);
      cloudBusy.value = true;
      const result = await getCloud(row.id);
      const source = result.has_source ? await cloudSource(result.id) : null;
      assertLease(owner, token);
      const project = parseProject(result.project_data);
      await port.apply({
        owner,
        draftId: crypto.randomUUID(),
        createdAt: result.created_at,
        updatedAt: result.updated_at,
        name: result.name,
        params: { ...project.params },
        paletteId: project.paletteId,
        project,
        source,
        sourceSize: { width: 0, height: 0 },
        cloud: cloudLink(result),
        cloudClientId: result.client_id,
      });
      assertLease(owner, token);
      await port.persist();
      cloudVisible.value = false;
      cloudConflict.value = false;
    } catch (error) {
      if (owner === port.owner.value) showError(error);
    } finally {
      if (owner === port.owner.value) cloudBusy.value = false;
    }
  }
  async function saveCloud(asNew = false) {
    if (cloudBusy.value || !port.project.value || port.changed.value) return;
    const before = port.snapshot();
    if (before.owner === "guest") {
      loginContinuation = true;
      try {
        if (
          !(await useAuthGateStore().requireAuthentication({
            reason: "登录后保存当前拼豆作品到云端",
          }))
        )
          return;
        const authorized = port.owner.value,
          token = lease(authorized);
        // 游客快照保留在闭包，登录清理视图后再显式复制；不覆盖游客原草稿。
        await port.readyWait();
        assertLease(authorized, token);
        if (port.owner.value !== authorized || authorized === "guest") return;
        await port.apply({
          ...before,
          owner: authorized,
          draftId: crypto.randomUUID(),
          cloud: undefined,
          cloudClientId: before.cloudClientId ?? before.draftId,
        });
        assertLease(authorized, token);
        await port.persist();
      } catch (error) {
        showError(error);
        return;
      } finally {
        loginContinuation = false;
      }
    }
    const owner = port.owner.value,
      token = lease(owner),
      snapshot = port.snapshot();
    if (!snapshot.project) return;
    cloudBusy.value = true;
    cloudError.value = "";
    cloudConflict.value = false;
    try {
      const project = parseProject({
        ...snapshot.project,
        name: snapshot.name.trim() || "我的拼豆图纸",
      });
      // 另存的客户端标识在发请求前持久化；未知网络结果重试不会再创建一份。
      if (asNew) {
        port.cloud.value = undefined;
        port.cloudClientId.value = crypto.randomUUID();
        await port.persist();
      }
      const link = asNew ? undefined : snapshot.cloud;
      const clientId = port.cloudClientId.value || snapshot.draftId;
      const result = await putCloud(
        project,
        snapshot.source,
        thumbnail(project.pattern, getPalette(project.paletteId).colors),
        clientId,
        link,
      );
      assertLease(owner, token);
      if (before.owner === "guest")
        await saveMigration({
          key: `${owner}/${before.draftId}`,
          owner,
          sourceId: before.draftId,
          fingerprint: JSON.stringify(before.project),
          cloud: cloudLink(result),
        });
      if (port.snapshot().draftId === snapshot.draftId) {
        port.cloud.value = cloudLink(result);
        await port.persist();
      }
      cloudError.value = "";
      ElMessage.success("作品已保存到云端");
      await refreshCloud();
    } catch (error) {
      if (owner === port.owner.value) showError(error);
    } finally {
      if (owner === port.owner.value && validLease(owner, token))
        cloudBusy.value = false;
    }
  }
  async function renameCloudItem(row: CloudItem) {
    const owner = port.owner.value,
      token = lease(owner);
    try {
      const answer = await ElMessageBox.prompt(
        "请输入作品名称",
        "重命名云端作品",
        {
          inputValue: row.name,
          inputPattern: /^.{1,128}$/,
          inputErrorMessage: "名称为 1–128 个字符",
        },
      );
      assertLease(owner, token);
      const result = await renameCloud(row, answer.value.trim());
      assertLease(owner, token);
      if (port.cloud.value?.id === row.id && port.project.value) {
        const snapshot = port.snapshot();
        snapshot.cloud = cloudLink(result);
        snapshot.name = result.name;
        snapshot.project = { ...snapshot.project!, name: result.name };
        await port.apply(snapshot);
        await port.persist();
      }
      await refreshCloud();
    } catch (error) {
      if (error instanceof Error) showError(error);
    }
  }
  async function removeCloud(row: CloudItem) {
    const owner = port.owner.value,
      token = lease(owner);
    try {
      await ElMessageBox.confirm(
        "云端作品将被软删除，本地副本不受影响。",
        `删除“${row.name}”？`,
        { type: "warning" },
      );
      assertLease(owner, token);
      await deleteCloud(row);
      assertLease(owner, token);
      if (port.cloud.value?.id === row.id) {
        port.cloud.value = undefined;
        port.cloudClientId.value = crypto.randomUUID();
        await port.persist();
      }
      await refreshCloud();
    } catch (error) {
      if (error instanceof Error) showError(error);
    }
  }
  function retentionChanged(value: boolean | string | number) {
    try {
      setKeepLocal(port.owner.value, !!value);
      retainLocal.value = !!value;
    } catch {
      ElMessage.error("浏览器禁止保存设置，请检查存储权限");
    }
  }
  async function openMigration(automatic = false) {
    if (automatic && loginContinuation) return;
    if (!signedIn.value) return;
    if (automatic && port.deferPrompt.value) {
      pendingPrompt = port.owner.value;
      return;
    }
    const owner = port.owner.value,
      token = lease(owner);
    try {
      const guest = await listDrafts("guest"),
        own = automatic ? [] : await listDrafts(owner);
      assertLease(owner, token);
      migrationRows.value = [...guest, ...own];
      migrationStatuses.value = {};
      selectedMigrations.value = [];
      migrationCompleted.value = 0;
      migrationTotal.value = 0;
      migrationSummary.value = "";
      for (const draft of migrationRows.value) {
        const old = await getMigration(owner, draft.id);
        assertLease(owner, token);
        migrationStatuses.value[draft.id] = old
          ? "已关联当前账号，可选择更新"
          : "待选择";
      }
      if (automatic) {
        migrationRows.value = migrationRows.value.filter(
          (draft) => migrationStatuses.value[draft.id] === "待选择",
        );
      }
      if (automatic && port.deferPrompt.value) {
        pendingPrompt = owner;
        return;
      }
      if (migrationRows.value.length && !loginContinuation)
        migrationVisible.value = true;
    } catch (error) {
      showError(error);
    }
  }
  async function migrate() {
    if (migrationBusy.value || !selectedMigrations.value.length) return;
    const owner = port.owner.value,
      token = lease(owner);
    // 固定本次勾选快照，重试只包含失败项，避免同步过程中选择变化影响批次。
    const selected = migrationRows.value.filter((draft) =>
      selectedMigrations.value.includes(draft.id),
    );
    if (!selected.length) return;
    const failed: string[] = [];
    migrationCompleted.value = 0;
    migrationTotal.value = selected.length;
    migrationSummary.value = "正在同步，请稍候…";
    migrationBusy.value = true;
    try {
      for (const draft of selected) {
        assertLease(owner, token);
        migrationStatuses.value[draft.id] = "正在同步…";
        try {
          const previous = await getMigration(owner, draft.id);
          assertLease(owner, token);
          const fingerprint = JSON.stringify(draft.project);
          if (previous && previous.fingerprint === fingerprint) {
            migrationStatuses.value[draft.id] = "已同步，无需重复上传";
            continue;
          }
          const result = await putCloud(
            draft.project,
            draft.source,
            draft.thumbnail,
            draft.id,
            previous?.cloud ?? draft.cloud,
          );
          assertLease(owner, token);
          await saveMigration({
            key: `${owner}/${draft.id}`,
            owner,
            sourceId: draft.id,
            fingerprint,
            cloud: cloudLink(result),
          });
          migrationStatuses.value[draft.id] = "同步成功，本地副本已保留";
        } catch (error) {
          assertLease(owner, token);
          migrationStatuses.value[draft.id] =
            `失败：${error instanceof Error ? error.message : "请重试"}`;
          failed.push(draft.id);
        } finally {
          if (owner === port.owner.value && validLease(owner, token))
            migrationCompleted.value++;
        }
      }
      assertLease(owner, token);
      if (owner !== port.owner.value) return;
      if (failed.length) {
        selectedMigrations.value = failed;
        migrationSummary.value = `已同步 ${selected.length - failed.length} 份，失败 ${failed.length} 份。失败项已保留勾选，可点击“同步所选作品”重试。`;
        ElMessage.warning(migrationSummary.value);
        return;
      }
      // 同步后展示真实云端列表，不替换用户正在编辑的图纸，也不新增路由跳转。
      cloudPage.value = 1;
      cloudKeyword.value = "";
      await refreshCloud();
      assertLease(owner, token);
      if (owner !== port.owner.value) return;
      migrationSummary.value = `已同步 ${selected.length} 份作品，本地副本已保留。`;
      migrationVisible.value = false;
      port.closeLocalLibrary();
      cloudVisible.value = true;
      ElMessage.success(migrationSummary.value);
    } catch (error) {
      if (owner === port.owner.value) showError(error);
    } finally {
      if (owner === port.owner.value && validLease(owner, token))
        migrationBusy.value = false;
    }
  }
  watch(
    port.owner,
    async (owner) => {
      loadSerial++;
      cloudRows.value = [];
      cloudTotal.value = 0;
      cloudVisible.value = false;
      cloudError.value = "";
      cloudConflict.value = false;
      cloudBusy.value = false;
      cloudLoading.value = false;
      migrationVisible.value = false;
      migrationRows.value = [];
      migrationStatuses.value = {};
      migrationCompleted.value = 0;
      migrationTotal.value = 0;
      migrationSummary.value = "";
      migrationBusy.value = false;
      pendingPrompt = "";
      retainLocal.value = keepLocal(owner);
      if (owner !== "guest") {
        void refreshCloud();
        void openMigration(true);
      }
    },
    { immediate: true, flush: "sync" },
  );
  // 登录原操作（例如私有选图）优先完成，迁移提示不叠在认证/选图弹窗上。
  watch(port.deferPrompt, (deferred) => {
    if (!deferred && pendingPrompt === port.owner.value) {
      pendingPrompt = "";
      void openMigration(true);
    }
  });
  return {
    cloudVisible,
    cloudBusy,
    cloudLoading,
    cloudError,
    cloudRows,
    cloudPage,
    cloudTotal,
    cloudKeyword,
    cloudConflict,
    retainLocal,
    migrationVisible,
    migrationBusy,
    migrationRows,
    selectedMigrations,
    migrationStatuses,
    migrationCompleted,
    migrationTotal,
    migrationSummary,
    signedIn,
    previewUrl,
    refreshCloud,
    openLibrary,
    openCloud,
    saveCloud,
    renameCloudItem,
    removeCloud,
    retentionChanged,
    openMigration,
    migrate,
    reloadCloud: () =>
      port.cloud.value ? openCloud({ id: port.cloud.value.id }) : openLibrary(),
  };
}
