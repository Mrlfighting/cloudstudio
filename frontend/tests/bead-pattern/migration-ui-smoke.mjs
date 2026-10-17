/** 前端迁移交互回归：合成网络失败，检查进度、失败重试和成功后的弹窗切换。 */
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
  writes = [],
  rows = [];
let failOnce = true,
  releaseFirst;
const firstRequest = new Promise((resolve) => {
  releaseFirst = resolve;
});
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request(),
      url = new URL(req.url());
    if (url.pathname.endsWith("/auth/check-auth"))
      return route.fulfill({ json: { authenticated: false } });
    if (url.pathname === "/api/v1/bead-patterns/" && req.method() === "POST") {
      const parsed = new Request(req.url(), {
        method: "POST",
        headers: req.headers(),
        body: req.postDataBuffer(),
      });
      const form = await parsed.formData(),
        project = JSON.parse(form.get("project"));
      writes.push(project.name);
      if (writes.length === 1) await firstRequest;
      if (project.name === "需要重试的作品" && failOnce) {
        failOnce = false;
        return route.fulfill({
          status: 503,
          json: { detail: "测试网络故障，请重试" },
        });
      }
      const row = {
        id: String(rows.length + 1),
        client_id: form.get("client_id"),
        revision: 1,
        name: project.name,
        width: 2,
        height: 2,
        palette_id: project.paletteId,
        has_source: false,
        has_thumbnail: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        project_data: project,
      };
      rows.push(row);
      return route.fulfill({ status: 201, json: row });
    }
    return route.fulfill({
      json: { data: rows, total_count: rows.length, has_more: false },
    });
  });
  await page.goto(frontend + "/pixel-beads");
  await page.locator(".bead-workshop").waitFor();
  await page.evaluate(async () => {
    const { saveDraft } = await import("/src/features/bead-pattern/storage.ts");
    for (const [id, name] of [
      ["11111111-1111-4111-8111-111111111111", "可以同步的作品"],
      ["22222222-2222-4222-8222-222222222222", "需要重试的作品"],
    ]) {
      await saveDraft({
        id,
        owner: "guest",
        source: null,
        thumbnail: null,
        createdAt: new Date().toISOString(),
        project: {
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
        },
      });
    }
    const { useAuthStore } = await import("/src/stores/auth.ts");
    useAuthStore().setUser({
      id: 101,
      username: "migrationqa",
      name: "迁移测试",
      user_role: "user",
      is_superuser: false,
    });
  });
  const migration = page.getByRole("dialog", {
    name: "选择本地作品同步到云端",
    exact: true,
  });
  const library = page.getByRole("dialog", {
    name: "我的云端拼豆作品",
    exact: true,
  });
  const drafts = page.getByRole("dialog", {
    name: "当前浏览器的本地草稿",
    exact: true,
  });
  await migration.waitFor();
  const sync = migration.getByRole("button", {
    name: "同步所选作品",
    exact: true,
  });
  assert.equal(await sync.isDisabled(), true);
  await migration
    .getByText("请先勾选需要同步的作品。", { exact: true })
    .waitFor();
  for (const checkbox of await migration.locator(".el-checkbox").all())
    await checkbox.click();
  await sync.click();
  await migration.getByRole("progressbar").waitFor();
  assert.equal(await migration.locator(".el-button.is-loading").count(), 1);
  assert.equal(await migration.locator(".el-checkbox.is-disabled").count(), 2);
  releaseFirst();
  await migration.getByText(/已同步 1 份，失败 1 份/).waitFor();
  assert.equal(await library.isVisible(), false);
  assert.equal(await migration.locator(".el-checkbox.is-checked").count(), 1);
  assert.equal(
    await migration.locator(".el-checkbox.is-checked").innerText(),
    "需要重试的作品 · 游客草稿",
  );
  checks.push(
    "手机端未选择有引导；同步显示进度；部分失败保留弹框并仅勾选失败项",
  );
  await sync.click();
  await migration.waitFor({ state: "hidden" });
  await library.waitFor();
  assert.equal(await library.locator(".cloud-item").count(), 2);
  assert.equal(writes.filter((name) => name === "可以同步的作品").length, 1);
  assert.equal(writes.filter((name) => name === "需要重试的作品").length, 2);
  checks.push("只重试失败作品，全部完成自动打开云端列表且无重复上传");
  await library.locator(".el-dialog__headerbtn").click();
  await page.getByRole("button", { name: /本地草稿/ }).click();
  await drafts
    .getByRole("button", { name: "选择本地作品迁移", exact: true })
    .click();
  await migration.waitFor();
  for (const checkbox of await migration.locator(".el-checkbox").all())
    await checkbox.click();
  await sync.click();
  await migration.waitFor({ state: "hidden" });
  await drafts.waitFor({ state: "hidden" });
  await library.waitFor();
  assert.equal(writes.length, 3);
  assert.equal(new URL(page.url()).pathname, "/pixel-beads");
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  checks.push("重复同步直接展示云端结果，同时关闭本地草稿弹框，路由不变");
  assert.deepEqual(errors, []);
  await mkdir(outputDir, { recursive: true });
  await page.screenshot({
    path: outputDir + "/migration-completed-mobile.png",
    fullPage: true,
  });
  await writeFile(
    outputDir + "/migration-ui-results.json",
    JSON.stringify({ checks, writes, errors }, null, 2),
  );
  console.log(JSON.stringify({ checks, writes, errors }, null, 2));
} finally {
  releaseFirst();
  await browser.close();
}
