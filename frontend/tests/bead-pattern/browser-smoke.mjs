/** 本地端到端验收脚本；使用外部 Playwright 运行环境，不增加产品依赖。 */
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import assert from 'node:assert/strict'

const [runtime, sourceFile, stressFile, outputDir] = process.argv.slice(2)
if (!runtime || !sourceFile || !stressFile || !outputDir) throw new Error('参数：Playwright 入口、普通测试图、压力测试图、输出目录')
const { chromium } = await import(pathToFileURL(runtime).href)
await mkdir(outputDir, { recursive: true })
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true,
  downloadsPath: path.join(outputDir,'downloads'),
})
// 每次运行用独立测试上下文，刷新仍保留数据，避免上一轮失败遗留工作区干扰。
const context = await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true})
const page = await context.newPage(), errors = [], measures = []
page.on('pageerror', (error) => { errors.push(error.message); console.log('PAGE_ERROR', error.message) })
page.on('console', (msg) => { if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) { errors.push(msg.text()); console.log('CONSOLE_ERROR', msg.text()) } })
await page.addInitScript(() => {
  window.__beadLongTasks = []
  if (PerformanceObserver.supportedEntryTypes.includes('longtask')) new PerformanceObserver((list) => window.__beadLongTasks.push(...list.getEntries().map((entry) => entry.duration))).observe({ type: 'longtask' })
})
async function open() { await page.goto('http://127.0.0.1:5173/pixel-beads'); await page.locator('.bead-workshop').waitFor() }
async function generate(label) {
  console.log('GENERATE', label)
  await page.evaluate(() => { window.__beadLongTasks = [] })
  const start = Date.now()
  await page.getByRole('button', { name: '生成拼豆图纸', exact: true }).click()
  await page.locator('.save-state').filter({ hasText: '已自动保存到当前浏览器' }).waitFor({ timeout: 90_000 })
  await page.locator('.generation-progress').waitFor({ state: 'hidden', timeout: 90_000 })
  measures.push({ label, wallMs: Date.now() - start, metrics: await page.locator('.result-metrics').innerText(), longTasks: await page.evaluate(() => window.__beadLongTasks) })
}
async function download(button, filename) {
  const promise = page.waitForEvent('download')
  await page.getByRole('button', { name: button, exact: true }).click()
  const result = await promise
  await result.saveAs(path.join(outputDir, filename))
  return path.join(outputDir, filename)
}
try {
  await open()
  assert.equal(await page.locator('.el-overlay:visible').count(), 0)
  await page.getByRole('button', { name: '私有空间导入', exact: true }).click()
  await page.getByRole('dialog').filter({ hasText: '登录后可从自己的私有空间导入拼豆原图' }).waitFor()
  await page.getByRole('dialog').filter({ hasText: '登录后可从自己的私有空间导入拼豆原图' }).locator('.el-dialog__headerbtn').click()
  assert.equal(new URL(page.url()).pathname, '/pixel-beads')
  await page.locator('input[type=file][accept^="image"]').setInputFiles(sourceFile)
  await page.locator('.source-preview img').waitFor()
  await generate('desktop-default-100')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: path.join(outputDir, 'desktop.png'), fullPage: true })
  const jsonPath = await download('备份项目 JSON', 'project.beads.json')
  const project = JSON.parse(await readFile(jsonPath, 'utf8'))
  assert.equal(project.pattern.width, 100); assert.equal(project.pattern.height, 75)
  assert.ok(new Set(project.pattern.cells.filter((n) => n >= 0)).size <= 40)
  assert.ok(!JSON.stringify(project).includes('sourceUrl'))
  const pngPath = await download('下载 PNG 图纸', 'pattern.png')
  const png = await readFile(pngPath)
  assert.equal(png.subarray(1, 4).toString(), 'PNG')
  assert.ok(png.readUInt32BE(16) <= 4096 && png.readUInt32BE(20) <= 4096)
  const csvPath = await download('下载 CSV 清单', 'materials.csv')
  const csv = await readFile(csvPath, 'utf8'), sum = project.pattern.cells.filter((n) => n >= 0).length
  assert.ok(csv.includes(`"合计","","","${sum}"`))
  await page.reload(); await page.locator('.bead-workshop').waitFor()
  await page.getByRole('button', { name: /本地草稿/ }).click()
  await page.getByRole('button', { name: '继续创作', exact: true }).first().click()
  await page.getByRole('button', { name: '继续', exact: true }).last().click()
  await page.locator('.el-message-box').last().waitFor({state:'hidden'})
  await page.locator('.result-metrics').waitFor(); await page.locator('.source-preview img').waitFor()
  // 最大规格使用高颜色变化样本，取消后旧图纸必须仍然有效。
  await page.locator('input[type=file][accept^="image"]').setInputFiles(stressFile)
  await page.getByRole('button', { name: '继续', exact: true }).last().click()
  await page.locator('.el-message-box').last().waitFor({state:'hidden'})
  await page.locator('.source-preview img').waitFor()
  await page.getByRole('slider').first().focus(); await page.getByRole('slider').first().press('End')
  await page.getByRole('spinbutton').first().fill('128'); await page.getByRole('spinbutton').first().press('Tab')
  await page.getByRole('button', { name: '生成拼豆图纸', exact: true }).click()
  await page.getByRole('button', { name: '取消生成', exact: true }).click()
  await page.locator('.generation-progress').waitFor({ state: 'hidden' })
  await page.locator('.save-state').filter({ hasText: '生成已取消' }).waitFor()
  await generate('desktop-stress-200-128')
  const stressProjectPath = await download('备份项目 JSON', 'stress.beads.json')
  const stressProject = JSON.parse(await readFile(stressProjectPath, 'utf8'))
  assert.equal(stressProject.pattern.cells.length, 40_000)
  assert.ok(new Set(stressProject.pattern.cells).size <= 128)
  await page.setViewportSize({ width: 390, height: 844 })
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: path.join(outputDir, 'mobile.png'), fullPage: true })
  // 模拟手机窄屏与较慢 CPU，仅作性能参考，不等同于真机数据。
  const session = await context.newCDPSession(page)
  await session.send('Emulation.setCPUThrottlingRate', { rate: 4 })
  await generate('mobile-emulated-stress-200-128-cpu4x')
  await page.getByRole('button', { name: /本地草稿/ }).click()
  await page.locator('.draft-item').filter({ has: page.getByText('source', { exact: true }) }).first().getByRole('button', { name: '继续创作', exact: true }).click()
  await page.getByRole('button', { name: '继续', exact: true }).last().click()
  await page.locator('.el-message-box').last().waitFor({state:'hidden'})
  await page.getByText('已恢复本地草稿', { exact: false }).waitFor()
  await generate('mobile-emulated-default-100-cpu4x')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: path.join(outputDir, 'mobile.png'), fullPage: true })
  await session.send('Emulation.setCPUThrottlingRate', { rate: 1 })
  await page.locator('input[type=file][accept=".json"]').setInputFiles(jsonPath)
  await page.getByRole('button', { name: '继续', exact: true }).last().click()
  await page.locator('.el-message-box').last().waitFor({state:'hidden'})
  await page.getByText('项目备份不含原图。可直接导出图纸；重新调参需另选图片。', { exact: true }).waitFor()
  assert.equal(await page.locator('.source-preview').count(), 0)
  assert.ok(await page.getByRole('button', { name: '生成拼豆图纸', exact: true }).isDisabled())
  // 认证与私有来源使用测试专用响应，不创建用户、不写入开发数据库。
  let userId = null, noPrivateSpace = false
  const sourceBytes = await readFile(sourceFile)
  await page.route('**/api/v1/auth/check-auth', (route) => route.fulfill({ json: { authenticated: userId !== null } }))
  await page.route('**/api/v1/auth/login', (route) => { userId = 101; return route.fulfill({ json: { csrf_token: 'local-qa-only' } }) })
  await page.route('**/api/v1/auth/logout', (route) => { userId = null; return route.fulfill({ json: { message: '已退出' } }) })
  await page.route('**/api/v1/users/me', (route) => route.fulfill({ json: { id: userId, name: '验收账号', username: 'beadtest', user_role: 'user', is_superuser: false, email: null, profile_image_url: '', is_deleted: false, email_verified: false } }))
  await page.route('**/api/v1/bead-patterns/?*', route => route.fulfill({json:{data:[],total_count:0}}))
  await page.route('**/api/v1/spaces/my', (route) => route.fulfill({ status: noPrivateSpace ? 404 : 200, json: noPrivateSpace ? { detail: '空间不存在' } : { id: 1, name: '验收空间', status: 'active' } }))
  await page.route('**/api/v1/spaces/my/pictures?*', (route) => route.fulfill({ json: { data: [{ id: 501, name: '验收私有图片', url: 'http://127.0.0.1:5173/bead-qa-thumbnail.png', pic_width: 1280, pic_height: 960, tags: [], category: '风景' }], total_count: 1, has_more: false } }))
  await page.route('**/bead-qa-thumbnail.png', (route) => route.fulfill({ body: sourceBytes, contentType: 'image/png' }))
  await page.route('**/api/v1/bead-patterns/sources/private/501', (route) => route.fulfill({ body: sourceBytes, contentType: 'image/png' }))
  await page.getByRole('button', { name: '私有空间导入', exact: true }).click()
  const login = page.getByRole('dialog').filter({ hasText: '登录后可从自己的私有空间导入拼豆原图' })
  await login.getByPlaceholder('请输入账号', { exact: true }).fill('beadtest')
  await login.getByPlaceholder('请输入密码', { exact: true }).fill('test-only-123')
  await login.locator('.auth-submit').click()
  const picker = page.getByRole('dialog', { name: '从我的私有空间导入', exact: true })
  await picker.waitFor()
  await picker.getByRole('button', { name: /验收私有图片/ }).click()
  await page.locator('.source-preview img').waitFor()
  assert.equal(await page.locator('.count-badge').innerText(), '0')
  const migration = page.getByRole('dialog', {name:'选择本地作品同步到云端',exact:true})
  await migration.waitFor(); await migration.getByRole('button',{name:'暂不同步',exact:true}).click()
  await generate('private-source-ui-fixture')
  noPrivateSpace = true
  await page.getByRole('button', { name: '私有空间导入', exact: true }).click()
  await picker.getByText('你还没有私有空间；也可以直接使用本地图片。', { exact: true }).waitFor()
  await picker.locator('.el-dialog__headerbtn').click()
  // 确认恢复期间换号，旧账号的草稿不能重新进入工作区。
  await page.getByRole('button', { name: /本地草稿/ }).click()
  await page.getByRole('button', { name: '继续创作', exact: true }).first().click()
  await page.getByRole('button', { name: '继续', exact: true }).waitFor()
  userId = 202
  await page.evaluate(async () => {
    const { useAuthStore } = await import('/src/stores/auth.ts')
    const auth = useAuthStore()
    auth.setUser({ ...auth.user, id: 202 })
  })
  // 换号直接关闭旧确认框，不能让旧账号操作继续，也不残留私有名称。
  await page.locator('.el-message-box').last().waitFor({state:'hidden'})
  assert.equal(await page.locator('.result-metrics').count(), 0)
  assert.equal(await page.locator('.source-preview').count(), 0)
  await page.reload(); await page.locator('.bead-workshop').waitFor()
  assert.equal(await page.locator('.count-badge').innerText(), '0')
  assert.equal(await page.locator('.result-metrics').count(), 0)
  userId = null
  await page.reload(); await page.locator('.bead-workshop').waitFor()
  await page.getByRole('button', { name: /本地草稿/ }).click()
  assert.equal(await page.getByText('验收私有图片', { exact: true }).count(), 0)
  await page.getByRole('dialog', { name: '当前浏览器的本地草稿', exact: true }).locator('.el-dialog__headerbtn').click()
  assert.equal(errors.length, 0, errors.join('\n'))
  await writeFile(path.join(outputDir, 'browser-results.json'), JSON.stringify({ passed: true, measures, errors }, null, 2))
  console.log(JSON.stringify({ passed: true, measures, errors }, null, 2))
} catch (error) {
  await page.screenshot({ path: path.join(outputDir, 'failure.png'), fullPage: true }).catch(() => {})
  await writeFile(path.join(outputDir, 'failure.txt'), String(error) + '\n' + await page.locator('body').innerText().catch(() => ''))
  throw error
} finally { await context.close(); await browser.close() }
