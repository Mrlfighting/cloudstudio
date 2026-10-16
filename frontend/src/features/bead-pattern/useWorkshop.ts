/** 独立工作台状态与数据流；账号切换、取消操作均通过代次隔离异步结果。 */
import { computed, onBeforeUnmount, reactive, ref, shallowRef, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import { useAuthGateStore } from "@/stores/authGate";
import { spaceApi } from "@/api/space";
import { http } from "@/api/http";
import type { PictureListItemRead } from "@/types/picture";
import { PALETTES, getPalette } from "./palettes.ts";
import { gridSize, usageOf } from "./core.ts";
import { prepareSource, sourcePixels } from "./image.ts";
import { createGenerator } from "./generation.ts";
import { listDrafts, saveDraft, deleteDraft } from "./storage.ts";
import { parseProject } from "./project.ts";
import { downloadPng, materialText, thumbnail } from "./export.ts";
import { DEFAULT_PARAMS, ENGINE_VERSION, PALETTE_REVISION } from "./types.ts";
import type { BeadDraft, BeadPatternProject } from "./types.ts";

export function useWorkshop() {
  const auth = useAuthStore(),
    gate = useAuthGateStore();
  const owner = computed(() => (auth.user ? `user:${auth.user.id}` : "guest"));
  const params = reactive({ ...DEFAULT_PARAMS }),
    paletteId = ref(PALETTES[0]!.id),
    name = ref("我的拼豆图纸");
  const project = shallowRef<BeadPatternProject | null>(null),
    source = ref<Blob | null>(null),
    sourceUrl = ref("");
  const sourceSize = ref({ width: 0, height: 0 }),
    cropFile = ref<File | null>(null),
    cropVisible = ref(false);
  const preparing = ref(false),
    running = ref(false),
    exporting = ref(false),
    progress = ref(0);
  const lastDuration = ref<number | null>(null),
    warnings = ref<string[]>([]),
    saveState = ref("尚未生成图纸");
  const drafts = shallowRef<BeadDraft[]>([]),
    draftsVisible = ref(false),
    draftId = ref<string>(crypto.randomUUID());
  const privateVisible = ref(false),
    privateLoading = ref(false),
    privateError = ref(""),
    noSpace = ref(false);
  const privateItems = ref<PictureListItemRead[]>([]),
    keyword = ref(""),
    page = ref(1),
    total = ref(0);
  const generator = createGenerator();
  let epoch = 0,
    task = 0,
    fileTask = 0,
    listTask = 0;
  const palette = computed(() => getPalette(paletteId.value));
  const resultPalette = computed(() =>
    project.value ? getPalette(project.value.paletteId) : palette.value,
  );
  const usage = computed(() =>
    project.value
      ? usageOf(project.value.pattern, resultPalette.value.colors)
      : [],
  );
  const totalBeads = computed(() =>
    usage.value.reduce((n, row) => n + row.count, 0),
  );
  const dimensions = computed(() =>
    sourceSize.value.width
      ? gridSize(
          sourceSize.value.width,
          sourceSize.value.height,
          params.longEdge,
        )
      : null,
  );
  const changed = computed(
    () =>
      !!project.value &&
      (project.value.paletteId !== paletteId.value ||
        JSON.stringify(project.value.params) !== JSON.stringify(params)),
  );

  function message(error: unknown): string {
    const e = error as {
      response?: { data?: { detail?: unknown } };
      message?: string;
    };
    return typeof e.response?.data?.detail === "string"
      ? e.response.data.detail
      : e.message || "操作失败，请稍后重试";
  }
  function resetSource(blob: Blob | null) {
    if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value);
    source.value = blob;
    sourceUrl.value = blob ? URL.createObjectURL(blob) : "";
  }
  function stop() {
    task++;
    generator.cancel();
    if (running.value)
      saveState.value = project.value
        ? "生成已取消，保留上一版图纸"
        : "生成已取消，可调整参数后重试";
    running.value = false;
    progress.value = 0;
  }
  async function refreshDrafts() {
    const scope = owner.value;
    try {
      const rows = await listDrafts(scope);
      if (owner.value === scope) drafts.value = rows;
    } catch (error) {
      if (owner.value === scope) saveState.value = message(error);
    }
  }
  async function persist() {
    if (!project.value) return;
    const scope = owner.value,
      id = draftId.value,
      snapshot = parseProject(project.value);
    const record: BeadDraft = {
      id,
      owner: scope,
      project: snapshot,
      source: source.value,
      thumbnail: thumbnail(
        snapshot.pattern,
        getPalette(snapshot.paletteId).colors,
      ),
    };
    try {
      await saveDraft(record);
      if (scope === owner.value && id === draftId.value) {
        saveState.value = "已自动保存到当前浏览器";
        await refreshDrafts();
      }
    } catch (error) {
      if (scope === owner.value) saveState.value = message(error);
    }
  }
  // 登录、退出和换号立即取消读图及计算，旧请求不能把私有结果带到新账号。
  watch(
    owner,
    () => {
      epoch++;
      fileTask++;
      listTask++;
      stop();
      resetSource(null);
      project.value = null;
      sourceSize.value = { width: 0, height: 0 };
      drafts.value = [];
      draftId.value = crypto.randomUUID();
      privateVisible.value = false;
      privateItems.value = [];
      preparing.value = false;
      privateLoading.value = false;
      cropVisible.value = false;
      cropFile.value = null;
      warnings.value = [];
      lastDuration.value = null;
      saveState.value = "草稿按当前账号隔离";
      void refreshDrafts();
    },
    { immediate: true },
  );
  async function confirmReplace(): Promise<boolean> {
    if (!project.value) return true;
    try {
      await ElMessageBox.confirm(
        "当前图纸将离开工作区。请确认已保存草稿，或先导出项目备份。",
        "切换图纸",
        { confirmButtonText: "继续", cancelButtonText: "留在当前图纸" },
      );
      return true;
    } catch {
      return false;
    }
  }
  async function loadImage(file: Blob, title: string, crop = false) {
    const scope = epoch,
      serial = ++fileTask;
    stop();
    preparing.value = true;
    try {
      const prepared = await prepareSource(file);
      if (scope !== epoch || serial !== fileTask) return;
      const bitmap = await createImageBitmap(prepared.blob);
      if (scope !== epoch || serial !== fileTask) {
        bitmap.close();
        return;
      }
      sourceSize.value = { width: bitmap.width, height: bitmap.height };
      bitmap.close();
      resetSource(prepared.blob);
      project.value = null;
      name.value = title.slice(0, 128) || "我的拼豆图纸";
      if (!crop) draftId.value = crypto.randomUUID();
      warnings.value = prepared.animated
        ? ["动画图片仅使用静态首帧转换。"]
        : [];
      saveState.value = "选择品牌和规格后生成图纸";
      lastDuration.value = null;
    } catch (error) {
      if (scope === epoch && serial === fileTask)
        ElMessage.error(message(error));
    } finally {
      if (scope === epoch && serial === fileTask) preparing.value = false;
    }
  }
  async function selected(event: Event) {
    const element = event.target as HTMLInputElement,
      file = element.files?.[0];
    element.value = "";
    if (file && (await confirmReplace()))
      await loadImage(file, file.name.replace(/\.[^.]+$/, ""));
  }
  async function generate() {
    if (!source.value || preparing.value) return;
    const current = ++task,
      scope = epoch,
      blob = source.value,
      selectedPalette = palette.value;
    const selectedParams = { ...params },
      title = name.value.trim() || "我的拼豆图纸";
    generator.cancel();
    running.value = true;
    progress.value = 0;
    saveState.value = "正在后台生成图纸…";
    try {
      const pixels = await sourcePixels(blob);
      if (current !== task || scope !== epoch) return;
      const output = await generator.run(
        { ...pixels, colors: selectedPalette.colors, params: selectedParams },
        (p) => {
          if (current === task) progress.value = p;
        },
      );
      if (current !== task || scope !== epoch) return;
      project.value = {
        format: "cloudatelier-bead-pattern",
        version: 1,
        engineVersion: ENGINE_VERSION,
        paletteRevision: PALETTE_REVISION,
        paletteId: selectedPalette.id,
        name: title,
        updatedAt: new Date().toISOString(),
        params: selectedParams,
        pattern: output.pattern,
      };
      lastDuration.value = output.durationMs;
      warnings.value = output.warnings;
      if (!output.pattern.cells.some((cell) => cell >= 0))
        warnings.value.push("图纸全部为空白；请关闭去背景或重新选择图片。");
      await persist();
    } catch (error) {
      if (
        current === task &&
        scope === epoch &&
        !(error instanceof DOMException && error.name === "AbortError")
      )
        ElMessage.error(message(error));
    } finally {
      if (current === task && scope === epoch) running.value = false;
    }
  }
  function crop() {
    if (source.value) {
      stop();
      cropFile.value = new File([source.value], "拼豆工作源.png", {
        type: "image/png",
      });
      cropVisible.value = true;
    }
  }
  function cropped(blob: Blob) {
    void loadImage(blob, name.value, true);
  }
  async function renameCurrent() {
    if (project.value) {
      project.value = {
        ...project.value,
        name: name.value.trim() || "我的拼豆图纸",
        updatedAt: new Date().toISOString(),
      };
      await persist();
    }
  }
  async function restore(draft: BeadDraft) {
    const scope = epoch;
    if (draft.owner !== owner.value || !(await confirmReplace())) return;
    // 确认框打开期间可能换号，必须复核而不能采用确认后的账号代次。
    if (scope !== epoch || draft.owner !== owner.value) return;
    try {
      const parsed = parseProject(draft.project);
      stop();
      fileTask++;
      preparing.value = false;
      let size = { width: 0, height: 0 };
      if (draft.source) {
        const bitmap = await createImageBitmap(draft.source);
        size = { width: bitmap.width, height: bitmap.height };
        bitmap.close();
      }
      if (scope !== epoch) return;
      resetSource(draft.source);
      sourceSize.value = size;
      project.value = parsed;
      name.value = parsed.name;
      paletteId.value = parsed.paletteId;
      Object.assign(params, parsed.params);
      draftId.value = draft.id;
      warnings.value = [];
      lastDuration.value = null;
      saveState.value = "已恢复本地草稿";
      draftsVisible.value = false;
    } catch (error) {
      ElMessage.error(message(error));
    }
  }
  async function renameDraft(draft: BeadDraft) {
    const scope = owner.value;
    try {
      const answer = await ElMessageBox.prompt("请输入图纸名称", "重命名草稿", {
        inputValue: draft.project.name,
        inputPattern: /^.{1,128}$/,
        inputErrorMessage: "名称需为 1–128 个字符",
      });
      if (scope !== owner.value) return;
      const updated = {
        ...draft,
        project: {
          ...draft.project,
          name: answer.value.trim() || "我的拼豆图纸",
          updatedAt: new Date().toISOString(),
        },
      };
      await saveDraft(updated);
      if (draft.id === draftId.value && project.value) {
        project.value = updated.project;
        name.value = updated.project.name;
      }
      await refreshDrafts();
    } catch (error) {
      if (error instanceof Error) ElMessage.error(message(error));
    }
  }
  async function removeDraft(draft: BeadDraft) {
    const scope = owner.value;
    try {
      await ElMessageBox.confirm(
        "删除后只能通过已导出的项目文件恢复。",
        `删除“${draft.project.name}”？`,
        { type: "warning" },
      );
      if (scope !== owner.value) return;
      await deleteDraft(draft.id, scope);
      if (draftId.value === draft.id) {
        draftId.value = crypto.randomUUID();
        saveState.value = "草稿已删除，当前画布仍可导出";
      }
      await refreshDrafts();
    } catch (error) {
      if (error instanceof Error) ElMessage.error(message(error));
    }
  }
  async function importProject(event: Event) {
    const element = event.target as HTMLInputElement,
      file = element.files?.[0];
    element.value = "";
    if (!file || !(await confirmReplace())) return;
    const scope = epoch;
    try {
      if (file.size > 4 * 1024 * 1024) throw new Error("项目文件不能超过 4MB");
      const parsed = parseProject(JSON.parse(await file.text()));
      if (scope !== epoch) return;
      stop();
      fileTask++;
      preparing.value = false;
      resetSource(null);
      sourceSize.value = { width: 0, height: 0 };
      project.value = parsed;
      name.value = parsed.name;
      paletteId.value = parsed.paletteId;
      Object.assign(params, parsed.params);
      draftId.value = crypto.randomUUID();
      lastDuration.value = null;
      warnings.value = [
        "项目备份不含原图。可直接导出图纸；重新调参需另选图片。",
      ];
      await persist();
    } catch (error) {
      ElMessage.error(message(error));
    }
  }
  async function privateList() {
    const scope = epoch,
      serial = ++listTask;
    privateLoading.value = true;
    privateError.value = "";
    privateItems.value = [];
    noSpace.value = false;
    try {
      await spaceApi.getMy();
      const data = await spaceApi.listPictures({
        page: page.value,
        items_per_page: 12,
        keyword: keyword.value || undefined,
      });
      if (scope === epoch && serial === listTask) {
        privateItems.value = data.data;
        total.value = data.total_count;
      }
    } catch (error) {
      if (scope !== epoch || serial !== listTask) return;
      if (
        (error as { response?: { status: number } }).response?.status === 404
      ) {
        noSpace.value = true;
        total.value = 0;
      } else privateError.value = message(error);
    } finally {
      if (scope === epoch && serial === listTask) privateLoading.value = false;
    }
  }
  async function openPrivate() {
    if (
      !(await gate.requireAuthentication({
        reason: "登录后可从自己的私有空间导入拼豆原图",
      }))
    )
      return;
    privateVisible.value = true;
    keyword.value = "";
    page.value = 1;
    await privateList();
  }
  async function importPrivate(item: PictureListItemRead) {
    const scope = epoch;
    if (!(await confirmReplace()) || scope !== epoch) return;
    privateLoading.value = true;
    try {
      const response = await http.get<Blob>(
        `/bead-patterns/sources/private/${item.id}`,
        { responseType: "blob" },
      );
      if (scope !== epoch) return;
      privateVisible.value = false;
      await loadImage(response.data, item.name);
    } catch (error) {
      if (scope === epoch) {
        const data = (error as { response?: { data?: unknown } }).response
          ?.data;
        let detail = message(error);
        if (data instanceof Blob) {
          try {
            const body = JSON.parse(await data.text());
            if (typeof body.detail === "string") detail = body.detail;
          } catch {
            /* 非 JSON 错误保留通用提示。 */
          }
        }
        if (scope === epoch) ElMessage.error(detail);
      }
    } finally {
      if (scope === epoch) privateLoading.value = false;
    }
  }
  async function png() {
    if (!project.value) return;
    exporting.value = true;
    try {
      await downloadPng(project.value);
    } catch (error) {
      ElMessage.error(message(error));
    } finally {
      exporting.value = false;
    }
  }
  async function copyList() {
    if (!project.value) return;
    try {
      await navigator.clipboard.writeText(materialText(project.value));
      ElMessage.success("备料清单已复制");
    } catch {
      ElMessage.warning("复制不可用，请下载 CSV 清单");
    }
  }
  onBeforeUnmount(() => {
    epoch++;
    fileTask++;
    listTask++;
    stop();
    resetSource(null);
  });
  return {
    auth,
    params,
    paletteId,
    name,
    project,
    source,
    sourceUrl,
    cropFile,
    cropVisible,
    preparing,
    running,
    exporting,
    progress,
    lastDuration,
    warnings,
    saveState,
    drafts,
    draftsVisible,
    privateVisible,
    privateLoading,
    privateError,
    noSpace,
    privateItems,
    keyword,
    page,
    total,
    palette,
    resultPalette,
    usage,
    totalBeads,
    dimensions,
    changed,
    refreshDrafts,
    selected,
    generate,
    crop,
    cropped,
    renameCurrent,
    restore,
    renameDraft,
    removeDraft,
    importProject,
    privateList,
    openPrivate,
    importPrivate,
    png,
    copyList,
    stop,
  };
}
