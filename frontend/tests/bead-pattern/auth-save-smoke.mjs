/** 真实会话/临时 PostgreSQL：已登录刷新、账号边界失步和旧请求隔离回归。 */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const [runtime, sourceFile, outputDir] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(runtime).href);
const frontend = process.env.BEAD_QA_FRONTEND_URL ?? "http://127.0.0.1:5175";
const browser = await chromium.launch({
  executablePath:
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  headless: true,
});
const checks = [],
  errors = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  page.on("pageerror", (error) => errors.push(error.message));
  let writes = 0;
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (
      url.pathname === "/api/v1/bead-patterns/" &&
      route.request().method() === "POST"
    )
      writes++;
    const response = await route.fetch({
      url: "http://127.0.0.1:8001" + url.pathname + url.search,
    });
    await route.fulfill({ response });
  });
  await page.goto(frontend + "/pictures");
  const account = "beadfix" + Date.now().toString(36);
  await page.evaluate(async (account) => {
    const response = await fetch("/api/v1/users/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account,
        password: "Test-only-123!",
        confirm_password: "Test-only-123!",
      }),
    });
    if (response.status !== 201) throw new Error("测试账号创建失败");
  }, account);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  const login = page
    .locator(".el-dialog")
    .filter({ has: page.getByPlaceholder("请输入账号", { exact: true }) });
  await login.getByPlaceholder("请输入账号", { exact: true }).fill(account);
  await login
    .getByPlaceholder("请输入密码", { exact: true })
    .fill("Test-only-123!");
  await login.locator(".auth-submit").click();
  await login.waitFor({ state: "hidden" });
  // 先登录再硬导航，覆盖页面加载前已存在真实服务端 Session 的情况。
  await page.goto(frontend + "/pixel-beads");
  await page.getByRole("button", { name: "云端作品", exact: true }).waitFor();
  await page
    .getByLabel("选择拼豆图片", { exact: true })
    .setInputFiles(sourceFile);
  await page.locator(".source-preview img").waitFor();
  await page.getByRole("button", { name: "生成拼豆图纸", exact: true }).click();
  await page.locator(".result-metrics").waitFor();
  await page
    .locator(".save-state")
    .filter({ hasText: /已自动保存/ })
    .waitFor();
  // 模拟热更新/监听未同步：认证 Store 已登录，拼豆辅助状态仍停在游客。
  const owner = await page.evaluate(async () => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    const { beadOwner } = await import("/src/features/bead-pattern/session.ts");
    const owner = `user:${useAuthStore().user.id}`;
    beadOwner.value = "guest";
    return owner;
  });
  await page.getByRole("button", { name: "保存到云端", exact: true }).click();
  await page
    .getByText("作品已保存到云端", { exact: true })
    .waitFor({ timeout: 10000 });
  assert.equal(writes, 1);
  const result = await page.evaluate(async () => {
    const { listCloud, getCloud } = await import(
      "/src/features/bead-pattern/cloudApi.ts"
    );
    const { beadOwner } = await import("/src/features/bead-pattern/session.ts");
    const list = await listCloud();
    const detail = await getCloud(list.data[0].id);
    return {
      owner: beadOwner.value,
      count: list.total_count,
      hasSource: detail.has_source,
      cells: detail.project_data.pattern.cells.length,
    };
  });
  assert.equal(result.owner, owner);
  assert.equal(result.count, 1);
  assert.equal(result.hasSource, true);
  assert.ok(result.cells > 0);
  checks.push(
    "已登录直接进入、辅助账号状态失步时实际写入 PostgreSQL 并读取完整作品",
  );

  // 等待中的旧请求不能在 Store 已退出而辅助监听失步时返回私有结果。
  const isolation = await page.evaluate(async () => {
    const { cloudRequest } = await import(
      "/src/features/bead-pattern/cloudApi.ts"
    );
    const { useAuthStore } = await import("/src/stores/auth.ts");
    const { beadOwner } = await import("/src/features/bead-pattern/session.ts");
    const auth = useAuthStore(),
      oldOwner = beadOwner.value;
    let started;
    const waiting = new Promise((resolve) => {
      started = resolve;
    });
    let finish;
    const response = new Promise((resolve) => {
      finish = resolve;
    });
    const pending = cloudRequest({
      url: "/isolated-test",
      adapter: async (config) => {
        started();
        await response;
        return {
          data: { private: true },
          status: 200,
          statusText: "OK",
          headers: {},
          config,
        };
      },
    }).then(
      () => "leaked",
      (error) => error.name,
    );
    await waiting;
    auth.reset();
    beadOwner.value = oldOwner;
    finish();
    const status = await pending;
    let guestError;
    try {
      await cloudRequest({ url: "/bead-patterns/" });
    } catch (error) {
      guestError = error.message;
    }
    return { status, guestError, owner: beadOwner.value };
  });
  assert.equal(isolation.status, "AbortError");
  assert.match(isolation.guestError, /请登录/);
  assert.equal(isolation.owner, "guest");
  checks.push("旧私有响应取消；登录 Store 为游客时不发送云端请求");
  assert.deepEqual(errors, []);
  await mkdir(outputDir, { recursive: true });
  await writeFile(
    outputDir + "/auth-save-results.json",
    JSON.stringify({ checks, writes, result, isolation }, null, 2),
  );
  console.log(JSON.stringify({ checks, writes, result, isolation }, null, 2));
} finally {
  await browser.close();
}
