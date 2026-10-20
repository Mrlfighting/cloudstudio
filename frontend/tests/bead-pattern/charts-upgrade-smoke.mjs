/** 安全依赖升级回归：实际管理员/个人分析页面、词云、主题、刷新与手机布局。 */
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
  calls = [];
let noSpace = false;
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (msg) => {
    if (
      msg.type() === "error" &&
      !msg.text().includes("Failed to load resource")
    )
      errors.push(msg.text());
  });
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url()),
      p = url.pathname;
    calls.push(p + url.search);
    let json = {};
    if (p.endsWith("/auth/check-auth")) json = { authenticated: true };
    else if (p.endsWith("/users/me"))
      json = {
        id: 901,
        username: "chartqa",
        name: "图表测试",
        user_role: "admin",
        is_superuser: true,
      };
    else if (p.endsWith("/gallery/overview"))
      json = {
        total_pictures: 120,
        total_size: 1024 ** 3,
        total_downloads: 1580,
      };
    else if (p.endsWith("/spaces/overview"))
      json = {
        total_spaces: 8,
        total_capacity: 10 * 1024 ** 3,
        total_used: 1024 ** 3,
        usage_rate: 10,
        avg_pictures_per_space: 15,
      };
    else if (p.endsWith("/my/overview"))
      json = {
        space_id: noSpace ? null : 7,
        picture_count: 48,
        max_count: 100,
        count_usage: 48,
        total_size: 50 * 1024 ** 2,
        max_size: 100 * 1024 ** 2,
        size_usage: 50,
      };
    else if (p.endsWith("/storage-trend"))
      json = [
        { period: "2026-10-18", total_size: 1024 },
        { period: "2026-10-19", total_size: 4096 },
      ];
    else if (p.endsWith("/trend"))
      json = [
        { period: "2026-10-18", count: 10 },
        { period: "2026-10-19", count: 26 },
        { period: "2026-10-20", count: 48 },
      ];
    else if (p.endsWith("/category"))
      json = [
        { category: "风景", count: 30, total_size: 3000, ratio: 0.6 },
        { category: "动物", count: 20, total_size: 2000, ratio: 0.4 },
      ];
    else if (p.endsWith("/tags"))
      json = [
        "风景",
        "自然",
        "猫咪",
        "旅行",
        "美食",
        "城市",
        "灵感",
        "创作",
        "插画",
        "科技",
      ].map((tag, i) => ({ tag, count: 50 - i * 3 }));
    else if (p.endsWith("/ranking"))
      json = [
        {
          space_id: 1,
          name: "摄影空间",
          user_id: 1,
          username: "test1",
          space_level: 0,
          total_count: 80,
          total_size: 1024 ** 2,
        },
        {
          space_id: 2,
          name: "灵感空间",
          user_id: 2,
          username: "test2",
          space_level: 0,
          total_count: 20,
          total_size: 512 ** 2,
        },
      ];
    else if (p.endsWith("/top-uploaders"))
      json = [
        { user_id: 1, name: "测试用户", username: "test1", count: 50 },
        { user_id: 2, name: "创作者", username: "test2", count: 30 },
      ];
    else if (p.endsWith("/top-pictures"))
      json = [
        { picture_id: 1, name: "风景作品", url: "", download_count: 50 },
        { picture_id: 2, name: "动物作品", url: "", download_count: 25 },
      ];
    return route.fulfill({ json });
  });
  await mkdir(outputDir, { recursive: true });
  async function rendered(count) {
    await page.waitForFunction((count) => {
      const charts = [...document.querySelectorAll(".base-chart")];
      if (charts.length !== count) return false;
      return charts.every((el) => {
        const canvas = el.querySelector("canvas");
        if (!canvas?.width || !canvas.height) return false;
        const pixels = canvas
          .getContext("2d")
          .getImageData(0, 0, canvas.width, canvas.height).data;
        let colored = 0;
        for (let i = 3; i < pixels.length; i += 128)
          if (pixels[i] > 0) colored++;
        return colored > 8;
      });
    }, count);
  }
  await page.goto(frontend + "/admin/analytics");
  await rendered(6);
  // 开发态读取实际实例，确认词云被注册且不是仅有空白 canvas；生产预览仍验证真实像素。
  const echartsResource = await page.evaluate(
    () =>
      performance
        .getEntriesByType("resource")
        .find((r) => /\/echarts\.js\?/.test(r.name))?.name,
  );
  if (echartsResource) {
    const models = await page.evaluate(async (resource) => {
      const echarts = await import(resource);
      return [...document.querySelectorAll(".base-chart")].map((el) => {
        const chart = echarts.getInstanceByDom(el);
        return {
          types: chart.getOption().series.map((s) => s.type),
          animation: chart.getOption().animation,
          display: chart.getZr().storage.getDisplayList().length,
        };
      });
    }, echartsResource);
    assert.ok(
      models.some((m) => m.types.includes("wordCloud") && m.display > 0),
    );
    assert.ok(models.every((m) => m.animation === false));
  }
  checks.push(
    "管理员六张图表真实绘制，词云/环图/柱状/折线正常，保留主题与减少动态效果",
  );
  const switched = page.waitForResponse((r) =>
    r.url().includes("/gallery/trend?granularity=week"),
  );
  await page.getByText("周", { exact: true }).click();
  await switched;
  await page.getByRole("button", { name: "刷新数据" }).click();
  await rendered(6);
  await page.screenshot({
    path: outputDir + "/admin-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await rendered(6);
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.screenshot({
    path: outputDir + "/admin-mobile.png",
    fullPage: true,
  });
  checks.push("管理员刷新/切换周粒度、手机布局和图表 resize 正常");
  await page.goto(frontend + "/analytics/my-space");
  await rendered(3);
  await page.getByRole("button", { name: "刷新数据" }).click();
  await rendered(3);
  await page.screenshot({
    path: outputDir + "/personal-mobile.png",
    fullPage: true,
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  noSpace = true;
  await page.getByRole("button", { name: "刷新数据" }).click();
  await page
    .getByRole("button", { name: "前往我的空间", exact: true })
    .waitFor();
  assert.equal(await page.locator(".base-chart").count(), 0);
  checks.push("个人三张图表、热门图片、手机刷新及无私有空间引导正常");
  assert.deepEqual(errors, []);
  await writeFile(
    outputDir + "/charts-results.json",
    JSON.stringify({ checks, calls, errors }, null, 2),
  );
  console.log(JSON.stringify({ checks, errors }, null, 2));
} finally {
  await browser.close();
}
