/** 本地工作区、存储配额失败和快速换号回归；接口仅用合成响应，不写开发库。 */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";
const [runtime, sourceFile, outputDir] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(runtime).href);
await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  headless: true,
});
const context = await browser.newContext(),
  page = await context.newPage(),
  errors = [],
  checks = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.route("**/api/v1/**", (route) => {
  const p = new URL(route.request().url()).pathname;
  if (p.endsWith("/auth/check-auth"))
    return route.fulfill({ json: { authenticated: false } });
  return route.fulfill({ json: { data: [], total_count: 0, has_more: false } });
});
try {
  await page.goto("http://127.0.0.1:5175/pixel-beads");
  await page
    .locator('input[type=file][accept^="image"]')
    .setInputFiles(sourceFile);
  await page.locator(".source-preview img").waitFor();
  await page.getByRole("spinbutton").first().fill("24");
  await page.getByRole("spinbutton").first().press("Tab");
  await page
    .locator(".save-state")
    .filter({ hasText: "工作区已自动保存" })
    .waitFor();
  await page.reload();
  await page.locator(".source-preview img").waitFor();
  assert.equal(await page.getByRole("spinbutton").first().inputValue(), "24");
  assert.equal(await page.locator(".result-metrics").count(), 0);
  checks.push("生成前图片与参数刷新恢复");
  await page.getByRole("button", { name: "生成拼豆图纸", exact: true }).click();
  await page.locator(".result-metrics").waitFor();
  await page.locator(".save-state").filter({ hasText: "已自动保存" }).waitFor();
  // 模拟浏览器真实 put 抛配额错误；旧结果仍应可导出，界面不得声称保存成功。
  await page.evaluate(() => {
    window.__beadPut = IDBObjectStore.prototype.put;
    IDBObjectStore.prototype.put = function (...args) {
      if (this.name === "workspaces")
        throw new DOMException("quota", "QuotaExceededError");
      return window.__beadPut.apply(this, args);
    };
  });
  await page.getByRole("spinbutton").first().fill("23");
  await page.getByRole("spinbutton").first().press("Tab");
  await page
    .locator(".save-state")
    .filter({ hasText: "本地存储失败或空间不足" })
    .waitFor();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "备份项目 JSON", exact: true })
    .click();
  await (
    await download
  ).saveAs(path.join(outputDir, "quota-backup.beads.json"));
  await page.evaluate(() => {
    IDBObjectStore.prototype.put = window.__beadPut;
  });
  await page.getByRole("spinbutton").first().fill("24");
  await page.getByRole("spinbutton").first().press("Tab");
  await page
    .locator(".save-state")
    .filter({ hasText: "工作区已自动保存" })
    .waitFor();
  checks.push("存储配额失败明确提示，图纸仍可备份");
  await page.evaluate(async () => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    useAuthStore().setUser({
      id: 101,
      username: "testa",
      name: "本地验收账号",
      user_role: "user",
      is_superuser: false,
    });
  });
  await page.locator(".source-preview").waitFor({ state: "hidden" });
  const migration = page.getByRole("dialog", {
    name: "选择本地作品同步到云端",
    exact: true,
  });
  await migration.waitFor();
  await migration
    .getByRole("button", { name: "暂不同步", exact: true })
    .click();
  await page
    .locator('input[type=file][accept^="image"]')
    .setInputFiles(sourceFile);
  await page.locator(".source-preview img").waitFor();
  await page.getByRole("button", { name: "生成拼豆图纸", exact: true }).click();
  await page.locator(".result-metrics").waitFor();
  await page.locator(".save-state").filter({ hasText: "已自动保存" }).waitFor();
  await page.locator(".persistence-controls .el-switch").click();
  const rejection = await page.evaluate(async () => {
    const { useAuthStore } = await import("/src/stores/auth.ts");
    const { saveWorkspace, loadWorkspace } = await import(
      "/src/features/bead-pattern/storage.ts"
    );
    const auth = useAuthStore(),
      previous = { ...auth.user },
      workspace = await loadWorkspace("user:101");
    const pending = saveWorkspace(workspace).then(
      () => false,
      (error) => error.name === "AbortError",
    );
    // 同一事件循环内快速换号再回来，也必须执行两次边界清理。
    auth.setUser({ ...previous, id: 202 });
    auth.setUser(previous);
    return await pending;
  });
  assert.equal(rejection, true);
  await page.waitForTimeout(800);
  assert.equal(await page.locator(".result-metrics").count(), 0);
  assert.equal(await page.locator(".source-preview").count(), 0);
  const remaining = await page.evaluate(async () => {
    const { listDrafts, loadWorkspace } = await import(
      "/src/features/bead-pattern/storage.ts"
    );
    return {
      own: (await listDrafts("user:101")).length,
      guest: (await listDrafts("guest")).length,
      workspace: await loadWorkspace("user:101"),
    };
  });
  assert.equal(remaining.own, 0);
  assert.ok(remaining.guest > 0);
  assert.ok(!remaining.workspace?.project && !remaining.workspace?.source);
  checks.push("快速 A→B→A 取消旧回写、清理屏障和游客隔离");
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(outputDir, "local-results.json"),
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, checks, errors }, null, 2));
} catch (error) {
  await writeFile(
    path.join(outputDir, "failure.txt"),
    String(error) + "\n" + (await page.locator("body").innerText()),
  );
  throw error;
} finally {
  await browser.close();
}
