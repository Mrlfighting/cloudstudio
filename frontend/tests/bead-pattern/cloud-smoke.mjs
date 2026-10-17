/** 真实临时 PostgreSQL + Session/CSRF 浏览器验收；先启动 serve_cloud_qa.py。 */
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
const [runtime, sourceFile, outputDir] = process.argv.slice(2);
if (!runtime || !sourceFile || !outputDir)
  throw new Error("参数：Playwright 入口、图片、输出目录");
const { chromium } = await import(pathToFileURL(runtime).href);
const frontend = process.env.BEAD_QA_FRONTEND_URL ?? "http://127.0.0.1:5175";
await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  headless: true,
});
const errors = [],
  checks = [],
  contexts = [];
const accountA = "beada" + Date.now().toString(36),
  accountB = "beadb" + Date.now().toString(36);
function record(check) {
  checks.push(check);
  console.log("PASS", check);
}
async function device() {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    acceptDownloads: true,
  });
  contexts.push(context);
  const page = await context.newPage();
  page.on("pageerror", (e) => {
    errors.push(e.message);
    console.log("PAGE_ERROR", e.stack);
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log("CONSOLE_ERROR", msg.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400)
      console.log("HTTP", response.status(), response.url());
  });
  // 仅测试代理，把真实接口转到隔离临时后端，产品代码和 Vite 配置不改。
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const response = await route.fetch({
      url: "http://127.0.0.1:8001" + url.pathname + url.search,
    });
    await route.fulfill({ response });
  });
  return page;
}
async function auth(page, account) {
  const dialog = page
    .locator(".el-dialog")
    .filter({ has: page.getByPlaceholder("请输入账号", { exact: true }) });
  await dialog.getByPlaceholder("请输入账号", { exact: true }).fill(account);
  await dialog
    .getByPlaceholder("请输入密码", { exact: true })
    .fill("Test-only-123!");
  await dialog.locator(".auth-submit").click();
  await dialog.waitFor({ state: "hidden" });
}
async function api(page, method = "get", suffix = "", data) {
  return page.evaluate(
    async ({ method, suffix, data }) => {
      const token =
        document.cookie
          .split("; ")
          .find((x) => x.startsWith("csrf_token="))
          ?.split("=")
          .slice(1)
          .join("=") ?? "";
      const response = await fetch("/api/v1/bead-patterns/" + suffix, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": decodeURIComponent(token),
        },
        body: data ? JSON.stringify(data) : undefined,
      });
      return { status: response.status, data: await response.json() };
    },
    { method, suffix, data },
  );
}
async function saved(page) {
  await page
    .locator(".save-state")
    .filter({ hasText: /已自动保存/ })
    .waitFor();
  await page.waitForTimeout(700);
}
async function generate(page) {
  await page.getByRole("button", { name: "生成拼豆图纸", exact: true }).click();
  await page.locator(".result-metrics").waitFor();
  await saved(page);
}
async function storeCounts(page, owner) {
  return page.evaluate(async (owner) => {
    const db = await new Promise((resolve, reject) => {
      const r = indexedDB.open("cloudatelier-bead-patterns");
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
    const read = (store) =>
      new Promise((resolve) => {
        const r = db.transaction(store).objectStore(store).getAll();
        r.onsuccess = () => resolve(r.result);
      });
    const drafts = await read("drafts"),
      workspaces = await read("workspaces");
    const version = db.version;
    db.close();
    return {
      drafts: drafts.filter((x) => x.owner === owner).length,
      workspace: workspaces.filter((x) => x.owner === owner).length,
      version,
    };
  }, owner);
}
const page = await device();
try {
  // 先建立旧版 v1 数据库，再进入新模块触发兼容升级。
  await page.goto(frontend + "/pictures");
  await page.evaluate(
    async (accounts) => {
      for (const account of accounts) {
        const r = await fetch("/api/v1/users/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account,
            password: "Test-only-123!",
            confirm_password: "Test-only-123!",
          }),
        });
        if (r.status !== 201) throw new Error("临时验收账号创建失败");
      }
    },
    [accountA, accountB],
  );
  const source = (await readFile(sourceFile)).toString("base64");
  await page.evaluate(async (source) => {
    const project = {
      format: "cloudatelier-bead-pattern",
      version: 1,
      engineVersion: "ciede2000-lanczos3-v1",
      paletteRevision: "178dafbc9e77d3de556550dbd058270200129186",
      paletteId: "mard-291-github",
      name: "旧版游客作品",
      updatedAt: "2026-10-16T00:00:00Z",
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
    const blob = new Blob(
      [Uint8Array.from(atob(source), (c) => c.charCodeAt(0))],
      { type: "image/png" },
    );
    const db = await new Promise((resolve, reject) => {
      const r = indexedDB.open("cloudatelier-bead-patterns", 1);
      r.onupgradeneeded = () =>
        r.result
          .createObjectStore("drafts", { keyPath: "id" })
          .createIndex("owner", "owner");
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
    await new Promise((resolve, reject) => {
      const tx = db.transaction("drafts", "readwrite");
      tx.objectStore("drafts").put({
        id: "11111111-1111-4111-8111-111111111111",
        owner: "guest",
        project,
        source: blob,
        thumbnail: null,
      });
      tx.oncomplete = resolve;
      tx.onerror = reject;
    });
    db.close();
  }, source);
  await page.goto(frontend + "/pixel-beads");
  await page.locator(".bead-workshop").waitFor();
  await page.getByRole("button", { name: /本地草稿/ }).click();
  await page.getByRole("button", { name: "继续创作", exact: true }).click();
  await page.locator(".source-preview img").waitFor();
  await page.waitForTimeout(800);
  await page.reload();
  await page.locator(".result-metrics").waitFor();
  await page.locator(".source-preview img").waitFor();
  assert.equal((await storeCounts(page, "guest")).version, 2);
  checks.push("旧草稿升级、Blob 恢复与刷新自动恢复");
  await page.getByRole("spinbutton").first().fill("35");
  await page.getByRole("spinbutton").first().press("Tab");
  await page.waitForTimeout(800);
  await page.reload();
  await page
    .getByText("参数已改变，请重新生成后再保存到云端。", { exact: true })
    .waitFor();
  assert.equal(await page.getByRole("spinbutton").first().inputValue(), "35");
  checks.push("编辑参数独立保存");
  await generate(page);
  await page.getByRole("button", { name: "保存到云端", exact: true }).click();
  await auth(page, accountA);
  await page.getByText("作品已保存到云端", { exact: true }).waitFor();
  let rows = (await api(page)).data.data;
  assert.equal(rows.length, 1);
  const original = rows[0];
  // 同一账号 CSRF 过期允许刷新后重试一次，区别于禁止重放的 401。
  await page.evaluate(() => {
    document.cookie = "csrf_token=stale-token; Path=/";
  });
  await page.getByRole("button", { name: "保存到云端", exact: true }).click();
  await page.waitForTimeout(600);
  assert.equal((await api(page)).data.data[0].revision, 2);
  checks.push("CSRF 过期刷新与同账号单次重试");
  checks.push("游客保存登录续接、真实 multipart 与 Session/CSRF");
  // 第二设备没有本地草稿，直接打开云端作品继续。
  const second = await device();
  await second.goto(frontend + "/pixel-beads");
  await second
    .getByRole("button", { name: "保存到云端", exact: true })
    .waitFor();
  await second.getByRole("button", { name: "登录", exact: true }).click();
  await auth(second, accountA);
  await second.getByRole("button", { name: "云端作品", exact: true }).click();
  await second
    .getByRole("button", { name: "打开作品", exact: true })
    .first()
    .click();
  await second.locator(".source-preview img").waitFor();
  await second.locator(".bead-form .el-input input").first().fill("跨设备更新");
  await second.locator(".bead-form .el-input input").first().press("Tab");
  await second.getByRole("button", { name: "保存到云端", exact: true }).click();
  await second.getByText("作品已保存到云端", { exact: true }).waitFor();
  assert.equal((await api(second)).data.data[0].revision, 3);
  checks.push("跨设备打开、修改及更新版本");
  await page.getByRole("button", { name: "保存到云端", exact: true }).click();
  await page
    .getByRole("button", { name: "从云端重新载入", exact: true })
    .waitFor();
  await page.getByRole("button", { name: "另存为新作品", exact: true }).click();
  await page.getByText("作品已保存到云端", { exact: true }).waitFor();
  assert.equal((await api(page)).data.total_count, 2);
  checks.push("版本冲突不覆盖、另存作品");
  await page.getByRole("button", { name: "云端作品", exact: true }).click();
  const library = page.getByRole("dialog", {
    name: "我的云端拼豆作品",
    exact: true,
  });
  await library
    .getByRole("button", { name: "重命名云端作品", exact: true })
    .first()
    .click();
  const prompt = page.getByRole("dialog", {
    name: "重命名云端作品",
    exact: true,
  });
  await prompt.locator("input").fill("保留的云端作品");
  await prompt.getByRole("button", { name: "确定", exact: true }).click();
  await library.getByText("保留的云端作品", { exact: true }).waitFor();
  await page.locator('.el-message-box').last().waitFor({state:'hidden'});
  await page.screenshot({
    path: path.join(outputDir, "cloud-desktop.png"),
    fullPage: true,
  });
  await library
    .getByRole("button", { name: "删除云端作品", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await page.waitForTimeout(500);
  assert.equal((await api(page)).data.total_count, 1);
  checks.push("云端重命名和软删除");
  await library.locator(".el-dialog__headerbtn").click();
  // 设置关闭保留，从公共页退出，根部监听仍应清理账号缓存。
  const account = await page.evaluate(async () => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    return useAuthStore().user.id;
  });
  await page.locator(".persistence-controls .el-switch").click();
  assert.equal(
    await page
      .getByRole("switch", { name: "退出后保留本地草稿" })
      .getAttribute("aria-checked"),
    "false",
  );
  await page.goto(frontend + "/pictures");
  // 硬导航先恢复 Cookie 登录态；不能在 check-auth 与 GET /me 之间撤销会话。
  await page.waitForFunction(async () => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    const auth = useAuthStore();
    return auth.initialized && auth.user !== null;
  });
  await page.evaluate(async () => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    await useAuthStore().logout();
  });
  await page.waitForTimeout(800);
  assert.equal((await storeCounts(page, `user:${account}`)).drafts, 0);
  assert.equal((await storeCounts(page, `user:${account}`)).workspace, 0);
  assert.ok((await storeCounts(page, "guest")).drafts >= 1);
  checks.push("离开拼豆页退出仍清理账号草稿、游客副本保留");
  await page.goto(frontend + "/pixel-beads");
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await auth(page, accountB);
  const migration = page.getByRole("dialog", {
    name: "选择本地作品同步到云端",
    exact: true,
  });
  await migration.waitFor();
  await migration.locator(".el-checkbox").first().click();
  await migration
    .getByRole("button", { name: "同步所选作品", exact: true })
    .click();
  await migration
    .waitFor({ state: "hidden" });
  await library.waitFor();
  assert.equal((await api(page)).data.total_count, 1);
  await library.locator(".el-dialog__headerbtn").click();
  await page.getByRole("button", { name: /本地草稿/ }).click();
  await page.getByRole("button", { name: "选择本地作品迁移", exact: true }).click();
  await migration.waitFor();
  await migration.locator(".el-checkbox").first().click();
  await migration
    .getByRole("button", { name: "同步所选作品", exact: true })
    .click();
  await migration.waitFor({ state: "hidden" });
  await library.waitFor();
  await page.getByRole("dialog", { name: "当前浏览器的本地草稿", exact: true }).waitFor({ state: "hidden" });
  assert.equal((await api(page)).data.total_count, 1);
  assert.equal((await api(page, "get", original.id)).status, 404);
  checks.push("迁移成功自动显示云端作品、关闭本地弹框、重复同步幂等与账号隔离");
  await page
    .getByRole("button", { name: "打开作品", exact: true })
    .first()
    .click();
  await page.locator(".result-metrics").waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForFunction(() => [...document.querySelectorAll('.el-overlay')].every(el => getComputedStyle(el).display === 'none'));
  await page.locator('.el-message').last().waitFor({state:'hidden'});
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: path.join(outputDir, "cloud-mobile.png"),
    fullPage: true,
  });
  checks.push("手机布局无横向溢出");
  // 服务端撤销会话，前端尚保留账号；保存只能发送一次且不自动登录重放。
  await page.evaluate(async () => {
    const token = document.cookie
      .split("; ")
      .find((x) => x.startsWith("csrf_token="))
      ?.split("=")[1];
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      headers: { "X-CSRF-Token": decodeURIComponent(token) },
    });
  });
  let writes = 0;
  page.on("request", (r) => {
    if (r.method() === "PUT" && r.url().includes("/bead-patterns/")) writes++;
  });
  await page.getByRole("button", { name: "保存到云端", exact: true }).click();
  await page.waitForTimeout(800);
  assert.equal(writes, 1);
  assert.equal(
    await page.getByPlaceholder("请输入账号", { exact: true }).count(),
    0,
  );
  checks.push("会话失效不重放旧写入");
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(outputDir, "cloud-results.json"),
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, checks, errors }, null, 2));
} catch (error) {
  await page
    .screenshot({ path: path.join(outputDir, "failure.png"), fullPage: true })
    .catch(() => {});
  await writeFile(
    path.join(outputDir, "failure.txt"),
    String(error) +
      "\n" +
      JSON.stringify(errors) +
      "\n" +
      (await page
        .locator("body")
        .innerText()
        .catch(() => "")),
  );
  throw error;
} finally {
  await browser.close();
}
