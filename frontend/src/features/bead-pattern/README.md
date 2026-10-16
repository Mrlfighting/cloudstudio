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

不修改旧 Service、图库表、下载计数或配额，不新增数据库表。UI 的本地选图不会上传服务器；图纸、清单和备份均在浏览器生成。

## 验证

```bash
cd frontend
npm run test:beads   # Node 22.18+ 或 Node 24 的原生 TypeScript / test 支持
npm run build
```

`tests/bead-pattern/browser-smoke.mjs` 可在已有 Playwright 环境下运行，接受运行环境入口、普通测试图片、压力图片和项目内输出目录四个参数。截图、浏览器数据和下载文件应放入被忽略的 `.cache/`，禁止提交测试账号和运行日志。
