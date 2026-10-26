/** 邮箱浏览器验收：Node内置CDP、独立无头Edge、全量模拟API，不连接真实发信服务。 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { openSync, closeSync } from 'node:fs'
import path from 'node:path'

const base = process.env.EMAIL_QA_FRONTEND_URL ?? 'http://127.0.0.1:5173'
const output = path.resolve(process.argv[2] ?? '../.cache/email-ui-20261021/browser')
await mkdir(output, { recursive: true })
const profile = path.join(output, 'profile-' + Date.now())
await mkdir(profile)
const edge = process.env.EMAIL_QA_EDGE ?? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const browserLog = openSync(path.join(output, 'browser.log'), 'a')
const child = spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank'], {
  windowsHide: true, stdio: ['ignore', browserLog, browserLog], env: { ...process.env, TEMP: output, TMP: output },
})
closeSync(browserLog)
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
let activePort
for (let index = 0; index < 120; index++) {
  try { activePort = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).trim().split(/\r?\n/); break } catch { await delay(100) }
}
assert.ok(activePort, '无头Edge未启动，退出码：' + child.exitCode)
const socket = new WebSocket(`ws://127.0.0.1:${activePort[0]}${activePort[1]}`)
await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
let sequence = 0
const waiting = new Map(), listeners = new Map(), failures = [], checks = []
function send(method, params = {}, sessionId) {
  const id = ++sequence
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { waiting.delete(id); reject(new Error('CDP超时：' + method)) }, 20000)
    waiting.set(id, { resolve, reject, timer })
    socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }))
  })
}
socket.onmessage = ({ data }) => {
  const message = JSON.parse(data)
  if (message.id && waiting.has(message.id)) {
    const item = waiting.get(message.id)
    waiting.delete(message.id)
    clearTimeout(item.timer)
    if (message.error) item.reject(new Error(message.error.message))
    else item.resolve(message.result)
  } else if (message.method) {
    for (const callback of listeners.get(message.sessionId) ?? []) callback(message)
  }
}
const user = (id = 101, verified = false) => ({ id, name: '测试创作者', username: 'emailuser' + id, email: 'before@example.com', email_verified: verified, profile_image_url: '', user_profile: '寻找灵感，记录创作。', is_deleted: false, tier_id: null, is_superuser: false, user_role: 'user', oauth_provider: null })
function fixture(authenticated = true, verified = false) {
  return { active: authenticated ? 101 : null, users: new Map([[101, user(101, verified)], [202, { ...user(202, false), email: 'second@example.com' }]]), pending: null, calls: [], mode: '', code: '012345', delivery: 'queued', retry: 2, confirmations: 0, statusDelay: 0, resendDeadline: 0 }
}
const picture = { id: 1, name: '公开测试图片', introduction: '仅用于前端模拟验收', category: '风景', tags: ['自然'], url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==', pic_width: 800, pic_height: 600, pic_size: 1024, pic_format: 'PNG', color_mode: 'RGB', download_count: 1, user_id: 101, created_at: '2026-10-21T00:00:00Z', updated_at: '2026-10-21T00:00:00Z' }
async function responseFor(state, request) {
  const url = new URL(request.url), method = request.method, suffix = url.pathname.replace('/api/v1', '')
  const headers = Object.fromEntries(Object.entries(request.headers).map(([key, value]) => [key.toLowerCase(), value]))
  let body
  try { body = request.postData ? JSON.parse(request.postData) : null } catch { body = Object.fromEntries(new URLSearchParams(request.postData)) }
  state.calls.push({ path: suffix, method, owner: headers['x-expected-user-id'], body })
  let status = 200, json = {}, extra = []
  const me = state.users.get(state.active)
  if (suffix === '/auth/check-auth') json = { authenticated: !!me }
  else if (suffix === '/auth/login') { state.active = body.username === 'other' ? 202 : 101; json = { csrf_token: 'test-csrf' } }
  else if (suffix === '/auth/logout') { state.active = null; json = { message: 'Logged out' } }
  else if (suffix === '/auth/refresh-csrf') json = { csrf_token: 'test-csrf-fresh' }
  else if (suffix === '/users/me') { if (me) json = me; else { status = 401; json = { detail: '未登录' } } }
  else if (suffix === '/users/register') {
    if (state.mode === 'occupied') { status = 409; json = { detail: '邮箱不可用，请更换邮箱' } }
    else { status = 201; state.users.get(101).email = null; state.pending = { request_id: '11111111-1111-4111-8111-111111111111', email: body.email, purpose: 'binding', expires_at: new Date(Date.now() + 600000).toISOString(), retry_after: state.retry, delivery_status: 'queued' }; json = { ...user(), email: null, email_verification: state.pending } }
  } else if (suffix.startsWith('/email/')) {
    if (!me) { status = 401; json = { detail: '未登录' } }
    else if (Number(headers['x-expected-user-id']) !== state.active) { status = 409; json = { detail: '账号已变更' }; extra.push({ name: 'X-Email-Session-Changed', value: '1' }) }
    else if (suffix === '/email/status') {
      if (state.pending && Date.parse(state.pending.expires_at) <= Date.now()) state.pending = null
      json = structuredClone({ email: me.email, email_verified: me.email_verified, pending: state.pending })
      if (json.pending && state.resendDeadline) json.pending.retry_after = Math.max(0, Math.ceil((state.resendDeadline - Date.now()) / 1000))
      if (state.statusDelay) await delay(state.statusDelay)
      if (state.mode === 'status-failure') { status = 503; json = { detail: '邮箱服务暂不可用' } }
    } else if (suffix.endsWith('/request')) {
      if (state.mode === 'session-expired') { state.active = null; status = 401; json = { detail: '登录已失效' } }
      else if (state.mode === 'rate') { status = 429; json = { detail: '请稍后再发送验证码' }; extra.push({ name: 'Retry-After', value: '7' }) }
      else if (state.mode === 'occupied') { status = 409; json = { detail: '邮箱不可用，请更换邮箱' } }
      else {
        state.pending = { request_id: '11111111-1111-4111-8111-111111111111', email: body.email, purpose: 'binding', expires_at: new Date(Date.now() + 600000).toISOString(), retry_after: state.retry, delivery_status: state.delivery }
        state.resendDeadline = Date.now() + state.retry * 1000
        status = 202; json = { ...state.pending, delivery_status: 'queued' }
      }
    } else if (suffix.endsWith('/confirm')) {
      if (state.mode === 'csrf' && headers['x-csrf-token'] !== 'test-csrf-fresh') { status = 403; json = { detail: 'CSRF已失效' }; extra.push({ name: 'X-CSRF-Error', value: '1' }) }
      else if (body.code !== state.code || !state.pending) { status = 400; json = { detail: '验证码错误或已失效' } }
      else { me.email = state.pending.email; me.email_verified = true; state.pending = null; state.confirmations++; json = { email: me.email, email_verified: true } }
    }
  } else if (suffix === '/pictures/') json = { data: [picture], total_count: 1, has_more: false, page: 1, items_per_page: 20 }
  else if (suffix === '/pictures/1') json = picture
  else if (suffix === '/pictures/1/similar') json = { results: [], data: [], total: 0 }
  else if (suffix === '/bead-patterns/') json = { data: [], total_count: 0 }
  else if (suffix === '/spaces/my') { status = 404; json = { detail: '尚未创建私有空间' } }
  else if (suffix.startsWith('/users/') && method === 'PATCH') { Object.assign(me, body); json = { message: '资料更新成功' } }
  else if (suffix === '/users/') json = { data: [...state.users.values()], total_count: 2, page: 1, items_per_page: 10, has_more: false }
  else { status = 404; json = { detail: '测试未配置此接口' } }
  return { responseCode: status, responseHeaders: [{ name: 'Content-Type', value: 'application/json; charset=utf-8' }, { name: 'Cache-Control', value: 'private, no-store' }, ...extra], body: Buffer.from(JSON.stringify(json)).toString('base64') }
}
async function tab(state, width = 1366, context) {
  const browserContextId = context ?? (await send('Target.createBrowserContext')).browserContextId
  const { targetId } = await send('Target.createTarget', { url: 'about:blank', browserContextId })
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })
  listeners.set(sessionId, [(event) => {
    if (event.method === 'Fetch.requestPaused') {
      void responseFor(state, event.params.request).then((result) => send('Fetch.fulfillRequest', { requestId: event.params.requestId, ...result }, sessionId)).catch(() => {})
    }
    if (event.method === 'Runtime.exceptionThrown') failures.push(event.params.exceptionDetails.exception?.description ?? event.params.exceptionDetails.text)
  }])
  await send('Runtime.enable', {}, sessionId)
  await send('Page.enable', {}, sessionId)
  await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/v1/*' }] }, sessionId)
  await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 }, sessionId)
  const evaluate = async (expression) => {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture: true }, sessionId)
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text)
    return result.result.value
  }
  const page = {
    context: browserContextId, sessionId, evaluate,
    async wait(expression, message = expression) {
      for (let index = 0; index < 180; index++) {
        if (await evaluate(expression)) return
        await delay(100)
      }
      throw new Error('等待超时：' + message)
    },
    async go(route) {
      await send('Page.navigate', { url: base + route }, sessionId)
      await page.wait("!!document.querySelector('.layout, .auth-shell')", '页面初始化')
    },
    click(text, parent = 'document') {
      return evaluate(`(()=>{const button=[...${parent}.querySelectorAll('button')].find(x=>x.textContent.trim()===${JSON.stringify(text)}&&x.getClientRects().length);if(!button)throw new Error('找不到按钮：'+${JSON.stringify(text)});button.click()})()`)
    },
    fill(selector, value) {
      return evaluate(`(()=>{const input=document.querySelector(${JSON.stringify(selector)});if(!input)throw new Error('找不到输入框');input.value=${JSON.stringify(value)};input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));input.dispatchEvent(new Event('blur'))})()`)
    },
    async shot(name) {
      // 等待有限的入场过渡完成，不关闭产品中的真实动效。
      await delay(800)
      const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, sessionId)
      await writeFile(path.join(output, name + '.png'), Buffer.from(shot.data, 'base64'))
    },
    async modules(expression) {
      return evaluate(`(async()=>{const {useEmailVerificationStore}=await import('/src/features/email-verification/store.ts');const {useAuthStore}=await import('/src/stores/auth.ts');const email=useEmailVerificationStore(),auth=useAuthStore();${expression}})()`)
    },
  }
  return page
}
function pass(name) { checks.push(name); console.log('通过：' + name) }
let current
try {
  // 游客注册：必填校验、错误提示和注册后的手动登录续接。
  let state = fixture(false), page = current = await tab(state)
  await page.go('/register')
  await page.wait("!!document.querySelector('input[autocomplete=email]')")
  await page.fill('input[autocomplete=username]', 'signup')
  await page.fill('input[autocomplete=new-password]', 'Test-only-123!')
  await page.evaluate("document.querySelectorAll('input[autocomplete=\"new-password\"]')[1].value='Test-only-123!';document.querySelectorAll('input[autocomplete=\"new-password\"]')[1].dispatchEvent(new Event('input',{bubbles:true}))")
  await page.click('注册')
  await page.wait("document.body.innerText.includes('请输入邮箱地址')")
  assert.equal(state.calls.filter(x => x.path === '/users/register').length, 0)
  pass('注册邮箱必填，不填写不发送请求')
  await page.fill('input[autocomplete=email]', 'not-an-email')
  await page.click('注册')
  await page.wait("document.body.innerText.includes('请输入正确的邮箱地址')")
  await page.fill('input[autocomplete=email]', ' signup@example.com ')
  state.mode = 'occupied'
  await page.click('注册')
  await page.wait("document.body.innerText.includes('邮箱不可用')")
  state.mode = ''
  await page.click('注册')
  await page.wait("location.pathname==='/login'")
  assert.equal(state.active, null)
  assert.equal(state.calls.filter(x => x.path === '/users/register').at(-1).body.email, 'signup@example.com')
  pass('格式校验、邮箱占用、注册成功后不自动登录')
  await page.fill('input[autocomplete=current-password]', 'Test-only-123!')
  await page.click('登录')
  await page.wait("document.querySelector('.email-verification-dialog')?.getClientRects().length>0")
  assert.equal(await page.evaluate("[...document.querySelectorAll('.auth-dialog')].some(x=>x.getClientRects().length>0)"), false)
  pass('独立登录后衔接验证码弹窗')
  await page.click('暂缓验证，继续浏览')
  await page.wait("location.pathname==='/pictures'")

  // 公共页的登录弹窗链路：注册、登录、邮箱验证、原上传弹窗依次衔接。
  state = fixture(false)
  page = current = await tab(state)
  await page.go('/pictures')
  await page.wait("document.body.innerText.includes('公开测试图片')")
  await page.click('上传图片')
  await page.wait("!!document.querySelector('.auth-dialog input[autocomplete=\"current-password\"]')")
  await page.click('去注册')
  await page.wait("!!document.querySelector('.auth-dialog input[autocomplete=email]')")
  await page.fill('.auth-dialog input[autocomplete=username]', 'modaluser')
  await page.fill('.auth-dialog input[autocomplete=email]', 'modal@example.com')
  await page.evaluate("document.querySelectorAll('.auth-dialog input[autocomplete=\"new-password\"]').forEach(x=>{x.value='Test-only-123!';x.dispatchEvent(new Event('input',{bubbles:true}))})")
  await page.click('注册', "document.querySelector('.auth-dialog')")
  await page.wait("!!document.querySelector('.auth-dialog input[autocomplete=\"current-password\"]')")
  await page.fill('.auth-dialog input[autocomplete=current-password]', 'Test-only-123!')
  await page.click('登录', "document.querySelector('.auth-dialog')")
  await page.wait("!!document.querySelector('.email-verification-dialog input[autocomplete=one-time-code]')")
  assert.equal(await page.evaluate("[...document.querySelectorAll('.el-dialog')].filter(x=>x.getClientRects().length&&x.innerText.includes('上传图片')&&x.querySelector('.el-upload')).length"), 0)
  await page.fill('input[autocomplete=one-time-code]', state.code)
  await page.click('确认验证邮箱')
  await page.wait("[...document.querySelectorAll('.el-dialog')].some(x=>x.getClientRects().length&&x.querySelector('.el-upload'))")
  assert.equal(state.confirmations, 1)
  pass('全局注册/登录/验证依次展示，验证后恢复原上传弹窗')

  // 浏览器原生下载没有Axios拦截器，必须通过同一验证门再执行一次。
  state = fixture(true)
  page = current = await tab(state)
  await page.go('/pictures/1')
  await page.wait("!!document.querySelector('.picture-detail-page')")
  await page.evaluate("window.__opens=[];window.open=(url)=>{window.__opens.push(url);return {opener:null}}")
  await page.click('下载原图')
  await page.click('下载原图')
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  assert.equal(await page.evaluate('window.__opens.length'), 0)
  await page.fill('.email-verification-dialog input[type=email]', 'download@example.com')
  await page.click('发送验证邮件')
  await page.wait("!!document.querySelector('input[autocomplete=one-time-code]')")
  await page.fill('input[autocomplete=one-time-code]', state.code)
  await page.click('确认验证邮箱')
  await page.wait('window.__opens.length===1')
  pass('已登录未验证账号下载仍被拦截，重复点击只续接一次')
  await page.evaluate("window.__fallbackDownloads=[];window.open=(url)=>url==='about:blank'?{opener:null,closed:false,location:{replace(target){window.__fallbackDownloads.push(target)}},close(){this.closed=true}}:null")
  await page.click('下载原图')
  await page.wait("document.body.innerText.includes('浏览器阻止了自动打开新窗口')")
  await page.click('继续下载')
  await page.wait('window.__fallbackDownloads.length===1')
  pass('浏览器阻止自动下载后，兜底按钮重新校验且只导航一次')

  // 已登录旧账号：公共浏览不弹窗，私有动作统一拦截并在验证后继续一次。
  state = fixture(true)
  page = current = await tab(state)
  await page.go('/pictures')
  await page.wait("document.body.innerText.includes('公开测试图片')")
  await page.modules('await email.refresh();return true')
  assert.equal(await page.modules('return email.visible'), false)
  await page.modules("void import('/src/api/space.ts').then(async({spaceApi})=>{try{await spaceApi.getMy();window.__privateBlocked=false}catch{window.__privateBlocked=true}})")
  await page.wait('window.__privateBlocked===true')
  assert.equal(state.calls.some(x => x.path === '/spaces/my'), false)
  pass('公共浏览可用，普通业务请求前置拦截')
  await page.modules("void import('/src/stores/authGate.ts').then(({useAuthGateStore})=>{window.__resumes=0;for(let i=0;i<2;i++)void useAuthGateStore().requireAuthentication().then(ok=>{if(ok)window.__resumes++})})")
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  await page.fill('.email-verification-dialog input[type=email]', 'new@example.com')
  await page.click('发送验证邮件')
  await page.wait("document.body.innerText.includes('邮件正在发送中')")
  assert.equal(await page.evaluate("document.body.innerText.includes('验证邮件已发送，请查收')"), false)
  assert.equal(state.calls.filter(x => x.path === '/email/binding/request').length, 1)
  state.pending.delivery_status = 'sent'
  state.pending.retry_after = 0
  await page.wait("document.body.innerText.includes('验证邮件已发送，请查收')")
  pass('202不虚报已发送，轮询投递状态并共用一个弹窗')
  await page.fill('input[autocomplete=one-time-code]', '000000')
  await page.click('确认验证邮箱')
  await page.wait("document.body.innerText.includes('验证码错误或已失效')")
  state.mode = 'csrf'
  await page.fill('input[autocomplete=one-time-code]', state.code)
  await page.click('确认验证邮箱')
  await page.wait('window.__resumes===2')
  assert.equal(state.confirmations, 1)
  assert.equal(state.users.get(101).email_verified, true)
  assert.equal(state.calls.filter(x => x.path === '/auth/refresh-csrf').length, 1)
  assert.ok(state.calls.filter(x => x.path.startsWith('/email/')).every(x => x.owner === '101'))
  pass('前导零验证码、错误提示、同账号CSRF单次重试及等待操作续接')
  await page.go('/profile')
  await page.wait("document.querySelector('.email-settings-card')?.innerText.includes('已验证')")
  await page.shot('profile-desktop')
  await page.click('更换邮箱')
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  assert.equal(await page.modules('return email.canUsePrivate'), true)
  await page.fill('.email-verification-dialog input[type=email]', 'changed@example.com')
  state.mode = ''
  await page.click('发送验证邮件')
  await page.wait("!!document.querySelector('input[autocomplete=one-time-code]')")
  assert.equal(state.users.get(101).email, 'new@example.com')
  await page.fill('input[autocomplete=one-time-code]', state.code)
  await page.click('确认验证邮箱')
  await page.wait("document.querySelector('.email-settings-card')?.innerText.includes('changed@example.com')")
  await page.go('/profile/edit')
  await page.wait("!!document.querySelector('.edit-profile-page')")
  assert.equal(await page.evaluate("!!document.querySelector('.edit-profile-page input[type=email]')"), false)
  await page.click('保存资料')
  await page.wait("location.pathname==='/profile'")
  assert.equal(Object.hasOwn(state.calls.findLast(x => x.method === 'PATCH' && x.path.startsWith('/users/')).body, 'email'), false)
  pass('换绑前保留原邮箱权限，完成后同步资料，资料PATCH不提交邮箱')

  // 深链与管理员不能绕过；服务不可用、429和账号变化保持失败关闭。
  state = fixture(true)
  state.users.get(101).user_role = 'admin'
  page = current = await tab(state)
  await send('Page.navigate', { url: base + '/admin/users' }, page.sessionId)
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  assert.equal(state.calls.some(x => x.path === '/users/'), false)
  await page.click('暂缓验证，继续浏览')
  await page.wait("location.pathname==='/pictures'")
  pass('未验证管理员深链受限，暂缓后返回探索')
  state.mode = 'rate'
  await page.modules('void email.openSettings()')
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  await page.fill('.email-verification-dialog input[type=email]', 'limit@example.com')
  await page.click('发送验证邮件')
  await page.wait("document.body.innerText.includes('7秒后可发送') || document.body.innerText.includes('6秒后可发送')")
  pass('429倒计时采用服务端Retry-After')
  await page.click('暂缓验证，继续浏览')
  state.mode = 'status-failure'
  await page.modules("void import('/src/stores/authGate.ts').then(({useAuthGateStore})=>useAuthGateStore().requireAuthentication())")
  await page.wait("document.body.innerText.includes('邮箱服务暂不可用')")
  assert.equal(await page.modules('return email.canUsePrivate'), false)
  await page.click('暂缓验证，继续浏览')
  pass('状态失败不放行且可暂缓浏览')
  state.mode = ''
  await page.modules('void email.openSettings()')
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  await page.fill('.email-verification-dialog input[type=email]', 'private@example.com')
  await page.modules("email.code='123456';auth.reset();return true")
  assert.equal(await page.modules("return email.code==='' && email.status===null && !email.visible"), true)
  pass('退出立即清空验证码、申请与私有邮箱视图')

  // 真实StorageEvent触发同账号状态同步，但通知本身不能充当认证结果。
  state = fixture(true)
  page = current = await tab(state)
  await page.go('/pictures')
  await page.modules("window.__crossVerified=null;void email.requireVerified().then(result=>window.__crossVerified=result)")
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  const sibling = await tab(state, 1366, page.context)
  await sibling.go('/profile')
  state.users.get(101).email_verified = true
  await sibling.evaluate("localStorage.setItem('cloudatelier.email.verified',JSON.stringify({owner:101,stamp:Date.now()}))")
  await page.wait('window.__crossVerified===true')
  pass('同账号跨标签页通知后查询服务端，自动完成等待中的验证门')
  state.active = 202
  await page.modules("email.code='999999';await email.refresh();return true")
  assert.equal(await page.modules("return auth.user===null && email.code==='' && email.status===null"), true)
  pass('旧标签页遇到服务端账号不一致409时清空旧视图')

  state = fixture(true)
  page = current = await tab(state)
  await page.go('/pictures')
  await page.modules('await email.refresh();return true')
  state.statusDelay = 1200
  await page.modules('void email.refresh();return true')
  await delay(100)
  state.active = 202
  await page.modules("email.code='654321';auth.setUser({...auth.user,id:202,username:'other',email:'second@example.com',email_verified:false});return true")
  await page.wait("(async()=>{const{useEmailVerificationStore}=await import('/src/features/email-verification/store.ts');const e=useEmailVerificationStore();return e.owner===202&&e.checked&&e.status?.email==='second@example.com'})()")
  assert.equal(await page.modules("return auth.user.id===202 && email.code==='' && email.status.email==='second@example.com'"), true)
  pass('快速换号时取消旧请求，迟到响应不能覆盖新账号状态')

  state = fixture(true)
  page = current = await tab(state)
  await page.go('/profile')
  await page.modules('await email.openSettings();return true')
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  state.mode = 'session-expired'
  await page.fill('.email-verification-dialog input[type=email]', 'expired@example.com')
  await page.click('发送验证邮件')
  await page.wait("(async()=>{const{useAuthStore}=await import('/src/stores/auth.ts');return !useAuthStore().user})()")
  state.mode = ''
  await page.modules("await auth.login('emailuser101','Test-only-123!');return true")
  assert.equal(state.calls.filter(x => x.path === '/email/binding/request').length, 1)
  pass('邮箱请求401后不自动重放，重新登录也不补发旧写入')

  state = fixture(true)
  state.delivery = 'failed'
  page = current = await tab(state)
  await page.go('/profile')
  await page.modules('await email.openSettings();return true')
  await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
  await page.fill('.email-verification-dialog input[type=email]', 'failed@example.com')
  await page.click('发送验证邮件')
  await page.wait("document.body.innerText.includes('邮件发送失败，请稍后重新发送')")
  state.pending.expires_at = new Date(Date.now() - 1000).toISOString()
  await page.modules('await email.refresh();return true')
  await page.wait("document.body.innerText.includes('验证申请已结束或过期')")
  assert.equal(state.calls.some(x => x.path === '/email/binding/confirm'), false)
  pass('投递失败与申请过期明确展示，不提交失效验证码')

  state = fixture(true)
  page = current = await tab(state)
  await page.go('/profile')
  await page.modules('await email.openSettings();return true')
  state.statusDelay = 1200
  await page.modules('void email.refresh();return true')
  await delay(100)
  await page.modules("email.address='fresh@example.com';return email.sendCode()")
  await delay(1400)
  assert.equal(await page.modules("return email.pending?.email==='fresh@example.com' && !email.editing"), true)
  pass('旧状态查询晚到时不能覆盖新验证码申请')

  // 手机布局以及游客拼豆工具不受邮件策略影响。
  for (const width of [360, 390]) {
    state = fixture(true)
    page = current = await tab(state, width)
    await page.go('/profile')
    await page.wait("!!document.querySelector('.email-settings-card')")
    await page.click('绑定并验证')
    await page.wait("!!document.querySelector('.email-verification-dialog input[type=email]')")
    assert.equal(await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), true)
    const bounds = await page.evaluate("(()=>{const r=document.querySelector('.email-verification-dialog').getBoundingClientRect();return {left:r.left,right:r.right,width:innerWidth,height:r.height}})()")
    assert.ok(bounds.left >= 0 && bounds.right <= bounds.width + 1)
    assert.ok(bounds.height < 700, '简单邮箱表单不应被全局移动端样式拉成满屏空白')
    await page.shot('email-mobile-' + width)
    await page.click('暂缓验证，继续浏览')
    await page.go('/pixel-beads')
    await page.wait("!!document.querySelector('.bead-workshop')")
    assert.equal(state.calls.some(x => x.path === '/bead-patterns/'), false)
    pass(width + 'px布局无横向溢出，未验证时本地拼豆可用且不加载云端')
  }
  assert.equal(failures.length, 0, failures.join('\n'))
  await writeFile(path.join(output, 'report.json'), JSON.stringify({ passed: checks.length, checks, browserErrors: failures }, null, 2))
  console.log(JSON.stringify({ passed: checks.length, browserErrors: failures.length }))
} catch (error) {
  if (current) await current.shot('failure').catch(() => {})
  await writeFile(path.join(output, 'failure.json'), JSON.stringify({ passed: checks, error: String(error), browserErrors: failures }, null, 2))
  console.error(error)
  process.exitCode = 1
} finally {
  await send('Browser.close').catch(() => {})
  socket.close()
  for (const item of waiting.values()) { clearTimeout(item.timer); item.reject(new Error('测试结束')) }
  waiting.clear()
}
