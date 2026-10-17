# 拼豆工坊独立模块

游客本地选图 → 可选裁剪 → LANCZOS 降采样 → Lab D65 / CIEDE2000 匹配 → 限色 / 去杂 → 图纸与备料清单。

## 代码来源与许可

- 流程参考：`527520/beadhue@d76cd9ef85cfdc1673033f8c259d586bf36b3827`。
- 参考仓库整体为 AGPL-3.0，实际引擎使用 Oklab 与盒式缩放。本模块没有复制其源代码、组件、测试或 AGPL 旧色卡。
- 算法依赖：pica 10.0.3（MIT，LANCZOS3）、Culori 4.0.2（MIT，Lab D65 / CIEDE2000）。依赖版权与许可由各自 npm 包保留。
- 色卡直接来自 `HansBug/pindou-color-data@178dafbc9e77d3de556550dbd058270200129186`，MIT 许可全文位于 `palettes/LICENSE`，原始 JSON 的 SHA-256 记录在 `palettes/sources.json`。运行时无需访问上游网络。
- 保持本项目 MIT 许可。颜色仅为屏幕参考，实际制作应核对品牌实体色卡。

## 职责与扩展点

- `core.ts`：纯算法，不访问 DOM、服务器或存储；按品牌色卡真实索引保存网格，`-1` 为空格。
- `generate.worker.ts` / `generation.ts`：独立、可终止的单任务 Worker，重新生成时销毁旧线程。预计算 Lab 和重复 RGB 缓存不改变精确 CIEDE2000 匹配。
- `image.ts`：校验实际签名与像素，方向纠正后将工作源缩至最长边 1600px；GIF / 动画 WebP 只用静态首帧。
- `project.ts` / `storage.ts`：版本化文件与账号分区的 IndexedDB。JSON 只含图纸与参数；本地草稿另存缩小 PNG，完整原图和远端 URL 不落入协议。
- `export.ts` / `PatternCanvas.vue`：共用图纸渲染、统计与导出。预览平移缩放只影响视图，不改写网格。
- `useWorkshop.ts`：处理来源、取消、认证续接、草稿和账号切换。旧请求使用代次隔离，不能覆盖新图纸或新账号。

## 接口与数据边界

私有空间浏览复用现有 `GET /spaces/my` 和 `GET /spaces/my/pictures`。新增同源读取 `GET /bead-patterns/sources/private/{picture_id}`，经后端只读适配器检验归属和封禁，再下载已配置 COS 来源的图片。

不修改旧 Service、图库表、下载计数或配额。转换、图纸和清单导出仍在浏览器进行；本地选图不会自动上传，只有点击云端保存或确认迁移才上传缩小工作源。

## 本地与云端持久化（2026-10-16）

- IndexedDB v2 兼容首版草稿，增加账号工作区、创建时间和迁移关系；尚未生成时的图片/参数也会防抖保存并自动恢复。旧草稿缺失创建时间时使用已有更新时间补齐。
- 独立 `bead_patterns` 表：项目 JSONB、最长边1600px的工作源 BYTEA、缩略图、账号归属、客户端标识、版本号与软删除。完整上传原图不落库，云端不会创建图库/空间记录。
- `/api/v1/bead-patterns/` 支持创建与分页列表；`/{id}` 支持详情/完整更新/重命名/软删除，`/{id}/source` 和 `/{id}/thumbnail` 也要求本人登录。图片不提供永久公开地址，列表不传图片或完整网格。
- `useCloudWorkshop.ts` / `cloudApi.ts`：手动云端保存、另存、作品管理和勾选迁移。版本冲突不覆盖；客户端标识防止重复创建。JSON备份协议不变，不包含云端关联、工作源或账号。
- `session.ts` / `BeadPersistenceBridge.vue`：应用根部只接线，监听全站退出/失效，默认保留账号本地草稿。关闭保留时清理该账号缓存；账号代次、请求终止和清理屏障阻止旧回写。清理失败留标记，下次登录重试。
- 云端使用独立 Axios 实例，Cookie/CSRF 与项目一致；401 不自动重放写入，CSRF刷新仅允许同账号重试一次。登录原操作完成后再显示迁移提示，避免叠加私有选图弹窗。
- 删除是软删除，工作源仍占数据库空间；本期没有回收站、自动物理清理或用户总容量套餐。

部署必须先备份并执行迁移 `e2b3c4d5f6a7`，再启动新后端；不要让启动自动建表先于 Alembic 创建同名表。只新增本模块表，不改用户或图库表。

## 验证

```bash
cd frontend
npm run test:beads   # Node 22.18+ 或 Node 24 的原生 TypeScript / test 支持
npm run build
```

`tests/bead-pattern/browser-smoke.mjs` 可在已有 Playwright 环境下运行，接受运行环境入口、普通测试图片、压力图片和项目内输出目录四个参数。截图、浏览器数据和下载文件应放入被忽略的 `.cache/`，禁止提交测试账号和运行日志。

云端端到端验证：先运行后端测试辅助入口 `tests/integration/api/v1/bead_pattern/serve_cloud_qa.py`（仅使用 Docker 临时数据库，端口8001），前端开发服务使用5175；再运行 `cloud-smoke.mjs <Playwright入口> <普通图片> <项目内输出目录>`。该脚本使用独立浏览器上下文模拟两设备，真实 Session/CSRF 与 PostgreSQL，无开发/生产库测试账号。`local-persistence-smoke.mjs` 用合成接口检查配额失败和快速换号，不写开发库。

`auth-save-smoke.mjs <Playwright入口> <普通图片> <项目内输出目录>` 使用同一隔离服务，覆盖已登录硬导航、辅助账号状态滞后时保存与真实数据库读回，以及旧账号响应取消。云端身份始终以现有登录 Store 为准；拼豆辅助状态仅负责隔离与清理，不能成为第二份登录凭据。

`migration-ui-smoke.mjs <Playwright入口> <项目内输出目录>` 使用合成接口覆盖手机端勾选、同步进度、部分失败只重试失败项，以及全部成功/重复同步后自动关闭迁移和本地草稿弹框、展示云端列表。同步不改变路由、不替换当前工作区。
