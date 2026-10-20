/** 真实临时 PostgreSQL：跨标签页隔离、未知创建结果恢复、删除/异设备修改后的迁移回归。 */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const [runtime, outputDir] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(runtime).href);
const frontend = process.env.BEAD_QA_FRONTEND_URL ?? "http://127.0.0.1:5175";
const browser = await chromium.launch({
  executablePath:
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  headless: true,
});
const errors = [],
  checks = [],
  creates = [];
let dropNext = false,
  activePage;
const accountA = "secua" + Date.now().toString(36),
  accountB = "secub" + Date.now().toString(36);
async function tab(context) {
  const page = await context.newPage();
  activePage = page;
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    if (
      request.method() === "POST" &&
      url.pathname === "/api/v1/bead-patterns/"
    ) {
      const parsed = new Request(request.url(), {
        method: "POST",
        headers: request.headers(),
        body: request.postDataBuffer(),
      });
      const form = await parsed.formData();
      creates.push(form.get("client_id"));
    }
    const response = await route.fetch({
      url: "http://127.0.0.1:8001" + url.pathname + url.search,
    });
    if (
      dropNext &&
      request.method() === "POST" &&
      url.pathname === "/api/v1/bead-patterns/"
    ) {
      dropNext = false;
      assert.equal(response.status(), 200);
      return route.fulfill({
        status: 502,
        json: { detail: "测试：服务端已保存但响应丢失" },
      });
    }
    await route.fulfill({ response });
  });
  await page.goto(frontend + "/pixel-beads");
  await page.locator(".bead-workshop").waitFor();
  return page;
}
function project(name) {
  return {
    format: "cloudatelier-bead-pattern",
    version: 1,
    engineVersion: "ciede2000-lanczos3-v1",
    paletteRevision: "178dafbc9e77d3de556550dbd058270200129186",
    paletteId: "mard-291-github",
    name,
    updatedAt: new Date().toISOString(),
    params: {
      longEdge: 100,
      maxColors: 40,
      removeBackground: false,
      backgroundColor: null,
      tolerance: 8,
      denoise: 0,
    },
    pattern: { width: 2, height: 2, cells: [0, 1, -1, 0] },
  };
}
async function login(page, account) {
  return page.evaluate(async (account) => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    const auth = useAuthStore();
    if (auth.user) await auth.logout();
    return (await auth.login(account, "Test-only-123!")).id;
  }, account);
}
async function api(page, method = "GET", suffix = "", body, expected) {
  return page.evaluate(
    async ({ method, suffix, body, expected }) => {
      const { useAuthStore } = await import("/src/stores/auth.ts");
      const token =
        document.cookie
          .split("; ")
          .find((x) => x.startsWith("csrf_token="))
          ?.slice(11) ?? "";
      const response = await fetch("/api/v1/bead-patterns/" + suffix, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": decodeURIComponent(token),
          "X-Bead-Owner": String(expected ?? useAuthStore().user?.id ?? ""),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      return { status: response.status, data: await response.json() };
    },
    { method, suffix, body, expected },
  );
}
async function importProject(page, name) {
  await page.getByLabel("导入拼豆项目", { exact: true }).setInputFiles({
    name: "安全回归.beads.json",
    mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify(project(name))),
  });
  await page.locator(".result-metrics").waitFor();
  await page.locator(".save-state").filter({ hasText: "已自动保存" }).waitFor();
}
async function idle(page) {
  await page.waitForFunction(
    () => !document.querySelector(".persistence-controls .is-loading"),
  );
}
function pass(message) {
  checks.push(message);
  console.log("PASS", message);
}
try {
  await mkdir(outputDir, { recursive: true });
  const shared = await browser.newContext(),
    first = await tab(shared);
  await first.evaluate(
    async (accounts) => {
      for (const account of accounts) {
        const response = await fetch("/api/v1/users/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account,
            password: "Test-only-123!",
            confirm_password: "Test-only-123!",
          }),
        });
        if (response.status !== 201) throw new Error("临时账号创建失败");
      }
    },
    [accountA, accountB],
  );
  const a = await login(first, accountA);
  await importProject(first, "账号A私有工作区");
  // 旧账号有未确认的创建时，跨页退出也必须清理这个新存储区，不能由B继续执行。
  dropNext = true;
  await first.getByRole("button", { name: "保存到云端", exact: true }).click();
  await first
    .locator(".cloud-error")
    .filter({ hasText: "服务端已保存但响应丢失" })
    .waitFor();
  const pendingBefore = await first.evaluate(async (owner) => {
    const { getPendingCreate, loadWorkspace } = await import(
      "/src/features/bead-pattern/storage.ts"
    );
    const workspace = await loadWorkspace(owner);
    return !!(await getPendingCreate(owner, workspace.draftId));
  }, `user:${a}`);
  assert.equal(pendingBefore, true);
  await first.locator(".persistence-controls .el-switch").click();
  const second = await tab(shared),
    b = await login(second, accountB);
  await first.waitForFunction(
    async (expected) =>
      (await import("/src/stores/auth.ts")).useAuthStore().user?.id ===
      expected,
    b,
  );
  await first.locator(".result-metrics").waitFor({ state: "hidden" });
  assert.equal((await api(second)).data.total_count, 0);
  const cache = await first.evaluate(async (owner) => {
    const { waitForOwner } = await import(
      "/src/features/bead-pattern/session.ts"
    );
    await waitForOwner(owner);
    const db = await new Promise((resolve) => {
      const req = indexedDB.open("cloudatelier-bead-patterns");
      req.onsuccess = () => resolve(req.result);
    });
    const count = (store) =>
      new Promise((resolve) => {
        const r = db
          .transaction(store)
          .objectStore(store)
          .index("owner")
          .count(owner);
        r.onsuccess = () => resolve(r.result);
      });
    const result = {
      drafts: await count("drafts"),
      pending: await count("cloudOperations"),
    };
    db.close();
    return result;
  }, `user:${a}`);
  assert.deepEqual(cache, { drafts: 0, pending: 0 });
  const guarded = await second.evaluate(
    async ({ expected, value }) => {
      const token = decodeURIComponent(
        document.cookie
          .split("; ")
          .find((x) => x.startsWith("csrf_token="))
          ?.slice(11) ?? "",
      );
      const data = new FormData();
      data.set("client_id", crypto.randomUUID());
      data.set("project", JSON.stringify(value));
      const response = await fetch("/api/v1/bead-patterns/", {
        method: "POST",
        headers: { "X-Bead-Owner": String(expected), "X-CSRF-Token": token },
        body: data,
      });
      return {
        status: response.status,
        changed: response.headers.get("x-bead-session-changed"),
      };
    },
    { expected: a, value: project("旧A请求不得写入B") },
  );
  assert.deepEqual(guarded, { status: 409, changed: "1" });
  assert.equal((await api(second)).data.total_count, 0);
  pass(
    "同浏览器换号清空旧视图/缓存；模拟通知延迟的旧账号请求在服务端拒绝，B库无A作品",
  );
  await second.evaluate(async () =>
    (await import("/src/stores/auth.ts")).useAuthStore().logout(),
  );
  await first.waitForFunction(
    async () => !(await import("/src/stores/auth.ts")).useAuthStore().user,
  );
  pass("其他页面退出会同步清除旧标签页登录态");

  const independent = await browser.newContext(),
    retry = await tab(independent);
  activePage = retry;
  await login(retry, accountA);
  const baseline = (await api(retry)).data.total_count;
  await importProject(retry, "另存冻结快照");
  await retry.getByRole("button", { name: "保存到云端", exact: true }).click();
  await retry.getByText("作品已保存到云端", { exact: true }).waitFor();
  await idle(retry);
  dropNext = true;
  await retry
    .getByRole("button", { name: "另存为新作品", exact: true })
    .click();
  await retry
    .locator(".cloud-error")
    .filter({ hasText: "服务端已保存但响应丢失" })
    .waitFor();
  await idle(retry);
  const countBefore = (await api(retry)).data.total_count;
  assert.equal(countBefore, baseline + 2);
  const name = retry.locator(".bead-form .el-input input").first();
  await name.fill("失败后的本地修改");
  await name.press("Tab");
  await retry
    .locator(".save-state")
    .filter({ hasText: /已自动保存/ })
    .waitFor();
  await retry.reload();
  await retry.getByRole("button", { name: "重试另存", exact: true }).waitFor();
  assert.equal(
    await retry.locator(".bead-form .el-input input").first().inputValue(),
    "失败后的本地修改",
  );
  await retry.getByRole("button", { name: "重试另存", exact: true }).click();
  await retry
    .getByRole("button", { name: "另存为新作品", exact: true })
    .waitFor();
  await idle(retry);
  assert.equal((await api(retry)).data.total_count, countBefore);
  assert.equal(creates.at(-1), creates.at(-2));
  await retry.getByRole("button", { name: "保存到云端", exact: true }).click();
  await idle(retry);
  await retry.waitForFunction(async () =>
    (
      await (
        await fetch("/api/v1/bead-patterns/", {
          headers: {
            "X-Bead-Owner": String(
              (await import("/src/stores/auth.ts")).useAuthStore().user.id,
            ),
          },
        })
      ).json()
    ).data.some((row) => row.name === "失败后的本地修改"),
  );
  pass(
    "另存落库后响应丢失，刷新/修改参数后仍复用冻结快照和同一UUID，无重复记录，后续可更新新作品",
  );

  const localId = crypto.randomUUID();
  await retry.evaluate(
    async ({ id, value }) => {
      const { useAuthStore } = await import("/src/stores/auth.ts");
      const { saveDraft } = await import(
        "/src/features/bead-pattern/storage.ts"
      );
      await saveDraft({
        id,
        owner: `user:${useAuthStore().user.id}`,
        project: value,
        source: null,
        thumbnail: null,
        createdAt: value.updatedAt,
      });
    },
    { id: localId, value: project("删除后重新同步") },
  );
  const migration = retry.getByRole("dialog", {
    name: "选择本地作品同步到云端",
    exact: true,
  });
  const library = retry.getByRole("dialog", {
    name: "我的云端拼豆作品",
    exact: true,
  });
  async function openMigration() {
    await retry.getByRole("button", { name: /本地草稿/ }).click();
    await retry
      .getByRole("button", { name: "选择本地作品迁移", exact: true })
      .click();
    await migration.waitFor();
    await migration
      .locator(".el-checkbox")
      .filter({ hasText: "删除后重新同步" })
      .click();
  }
  await openMigration();
  await migration
    .getByRole("button", { name: "同步所选作品", exact: true })
    .click();
  await migration.waitFor({ state: "hidden" });
  await library.waitFor();
  const original = (await api(retry)).data.data.find(
    (row) => row.name === "删除后重新同步",
  );
  assert.ok(original);
  assert.equal(
    (await api(retry, "DELETE", `${original.id}?revision=${original.revision}`))
      .status,
    200,
  );
  await library.locator(".el-dialog__headerbtn").click();
  await openMigration();
  await migration
    .getByRole("button", { name: "同步所选作品", exact: true })
    .click();
  await migration.getByText(/云端作品已删除或不可访问/).waitFor();
  assert.equal(await library.isVisible(), false);
  assert.equal(
    (await api(retry)).data.data.some((row) => row.id === original.id),
    false,
  );
  dropNext = true;
  await migration
    .getByRole("button", { name: "作为新作品同步", exact: true })
    .click();
  await retry
    .locator(".el-message-box")
    .getByRole("button", { name: "作为新作品同步", exact: true })
    .click();
  await migration.getByText(/服务端已保存但响应丢失/).waitFor();
  await migration
    .getByRole("button", { name: "同步所选作品", exact: true })
    .click();
  await migration.waitFor({ state: "hidden" });
  await library.waitFor();
  const restored = (await api(retry)).data.data.filter(
    (row) => row.name === "删除后重新同步",
  );
  assert.equal(restored.length, 1);
  assert.notEqual(restored[0].id, original.id);
  assert.equal(creates.at(-1), creates.at(-2));
  assert.equal((await api(retry, "GET", original.id)).status, 404);
  pass(
    "软删后重新同步不误报成功；用户确认新建后可恢复副本，响应丢失重试仍只有一份，原记录保持软删",
  );
  const changed = await api(retry, "PATCH", restored[0].id, {
    name: "异设备改名",
    revision: restored[0].revision,
  });
  assert.equal(changed.status, 200);
  await library.locator(".el-dialog__headerbtn").click();
  await openMigration();
  await migration
    .getByRole("button", { name: "同步所选作品", exact: true })
    .click();
  await migration.getByText(/云端作品已在其他设备修改/).waitFor();
  assert.equal(
    (await api(retry, "GET", restored[0].id)).data.name,
    "异设备改名",
  );
  pass("相同本地指纹也检查远端版本，不静默覆盖异设备修改");
  await retry.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await retry.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await retry.screenshot({
    path: outputDir + "/migration-security-mobile.png",
    fullPage: true,
  });
  // 同账号同时创建同一工作区的待确认任务，不能互相替换幂等标识或冻结内容。
  const peer = await tab(independent);
  const operationId = crypto.randomUUID();
  async function reserve(page, label) {
    return page.evaluate(
      async ({ id, value }) => {
        const { useAuthStore } = await import("/src/stores/auth.ts");
        const { savePendingCreate } = await import(
          "/src/features/bead-pattern/storage.ts"
        );
        const owner = `user:${useAuthStore().user.id}`;
        return savePendingCreate({
          key: `${owner}/workshop/${id}`,
          owner,
          draftId: id,
          scope: "workshop",
          clientId: crypto.randomUUID(),
          asNew: true,
          project: value,
          source: null,
          thumbnail: null,
        });
      },
      { id: operationId, value: project(label) },
    );
  }
  const [reservedA, reservedB] = await Promise.all([
    reserve(retry, "并发快照A"),
    reserve(peer, "并发快照B"),
  ]);
  assert.equal(reservedA.clientId, reservedB.clientId);
  assert.deepEqual(reservedA.project, reservedB.project);
  await peer.evaluate(async (value) => {
    const { deletePendingCreate } = await import(
      "/src/features/bead-pattern/storage.ts"
    );
    await deletePendingCreate(value);
  }, reservedA);
  pass("同账号两个标签页并发预留创建任务时，只保留同一个UUID与冻结快照");

  const quotaContext = await browser.newContext(),
    quota = await tab(quotaContext);
  activePage = quota;
  await login(quota, accountA);
  await importProject(quota, "存储故障后确认关联");
  await quota.evaluate(() => {
    const original = IDBObjectStore.prototype.put;
    window.__originalPut = original;
    window.__blockedStore = "cloudOperations";
    IDBObjectStore.prototype.put = function (...args) {
      if (this.name === window.__blockedStore)
        throw new DOMException("测试配额不足", "QuotaExceededError");
      return original.apply(this, args);
    };
  });
  const requestCount = creates.length;
  await quota.getByRole("button", { name: "保存到云端", exact: true }).click();
  await quota
    .locator(".cloud-error")
    .filter({ hasText: "待确认任务保存失败" })
    .waitFor();
  assert.equal(creates.length, requestCount);
  // 服务端成功、本地关联落盘失败时，保留待确认任务，重试不得再建一份。
  await quota.evaluate(() => {
    window.__blockedStore = "workspaces";
  });
  await quota.getByRole("button", { name: "保存到云端", exact: true }).click();
  await quota
    .locator(".cloud-error")
    .filter({ hasText: "本地关联尚未确认" })
    .waitFor();
  const savedCount = (await api(quota)).data.total_count;
  assert.equal(creates.length, requestCount + 1);
  await quota.evaluate(() => {
    IDBObjectStore.prototype.put = window.__originalPut;
  });
  await quota
    .getByRole("button", { name: "重试云端保存", exact: true })
    .click();
  await quota
    .getByRole("button", { name: "保存到云端", exact: true })
    .waitFor();
  await idle(quota);
  assert.equal((await api(quota)).data.total_count, savedCount);
  assert.equal(creates.at(-1), creates.at(-2));
  pass(
    "本地配额失败时先阻止未登记请求；云端成功但关联落盘失败时保留任务，重试只确认原记录",
  );
  assert.deepEqual(errors, []);
  await writeFile(
    outputDir + "/security-results.json",
    JSON.stringify({ checks, creates, errors }, null, 2),
  );
} catch (error) {
  await writeFile(
    outputDir + "/failure.txt",
    String(error) +
      "\n" +
      JSON.stringify(errors) +
      "\n" +
      (await activePage
        .locator("body")
        .innerText()
        .catch(() => "")),
  );
  await activePage
    .screenshot({ path: outputDir + "/failure.png", fullPage: true })
    .catch(() => {});
  throw error;
} finally {
  await browser.close();
}
