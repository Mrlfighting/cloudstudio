# 邮箱验证与异步欢迎邮件

独立后端模块。API只做账号/CSRF校验和数据库事务，不连接SMTP或RabbitMQ；调度器把任务ID投递到独立RabbitMQ队列，Taskiq worker读取加密任务并异步发信。没有引入Celery，也不接管现有注册校验、密码加密、会话或OAuth。

本期没有前端入口。现有注册页面仍只提交账号密码；旧资料页不能直接改绑邮箱，原样提交邮箱仍可修改昵称、头像和简介。后续页面应按下面协议接入，不能继续用资料PATCH更新邮箱。

## 运行前配置

实际配置读取**项目根目录 `.env`**，示例位于 `backend/.env.example`。默认 `MAIL_ENABLED=false`；开启时校验必要配置，但不在API启动阶段检查SMTP是否在线。

仓库现有本地Docker Compose的 `env_file` 指向 **`backend/.env`**，所以本地两份实际配置都需保存相同的24项邮件参数。两者均为Git忽略文件；新增或调整邮件参数时同步修改，避免手动启动与Compose读取不同值。此约定不改变既有配置加载器，进程环境变量仍优先于文件；上线模板继续只保留占位。

| 配置 | 用途/默认值 |
|---|---|
| `MAIL_ENABLED` | 邮件功能开关，默认false |
| `MAIL_SMTP_HOST` / `MAIL_SMTP_PORT` | QQ默认smtp.qq.com / 465 |
| `MAIL_SMTP_USERNAME` | 完整QQ邮箱地址 |
| `MAIL_SMTP_PASSWORD` | 在QQ邮箱开启SMTP后生成的授权码，不是登录密码 |
| `MAIL_SMTP_FROM` | 实际发件邮箱；QQ应使用该账号有权发送的地址 |
| `MAIL_SMTP_USE_TLS` / `MAIL_SMTP_START_TLS` | 默认true/false，不可同时开启 |
| `MAIL_SMTP_ALLOW_INSECURE` | 默认false，只在本机Mailpit测试中允许true |
| `MAIL_SMTP_TIMEOUT` | 整体发送超时20秒，含SMTP握手和发送 |
| `MAIL_TOKEN_SECRET` | 至少32字节的独立随机验证码摘要密钥 |
| `MAIL_PAYLOAD_ENCRYPTION_KEY` | 独立Fernet密钥，用于加密待发验证码载荷 |
| `MAIL_PUBLIC_BASE_URL` | https://cloudatelier.online；只允许HTTPS无凭据地址 |
| `MAIL_SUPPORT_EMAIL` | 可选，配置后显示邮件联系方式 |
| `MAIL_QUEUE_NAME` | 独立队列cloudatelier.email，自动使用独立交换机和死信队列 |
| `MAIL_CODE_TTL_SECONDS` / `MAIL_RESEND_SECONDS` | 600 / 60秒 |
| `MAIL_CODE_MAX_ATTEMPTS` | 每份验证码最多5次错误 |
| `MAIL_ACCOUNT_HOUR_LIMIT` / `MAIL_ADDRESS_HOUR_LIMIT` / `MAIL_IP_HOUR_LIMIT` | 账号/目标邮箱每小时5次，可信来源IP每小时20次 |
| `MAIL_SEND_PER_MINUTE` | 所有worker共享，每分钟最多10封，非QQ官方额度承诺 |
| `MAIL_POLL_SECONDS` / `MAIL_LEASE_SECONDS` | 调度间隔2秒、恢复租约120秒 |

RabbitMQ连接复用 `TASKIQ_RABBITMQ_HOST/PORT/USER/PASSWORD/VHOST`；邮件独立使用RabbitMQ，不要求修改既有 `TASKIQ_BROKER_TYPE`，不占用协同编辑或default任务队列。Redis限流复用 `RATE_LIMITER_REDIS_*`，**即使全站普通限流开关关闭，邮件限流仍启用且故障拒绝发送**。生产部署需按实际配置可信代理层数 `TRUSTED_PROXY_HOPS`，不要盲目信任请求中的X-Forwarded-For。

仅在本地终端生成密钥，然后分别写入未跟踪的实际 `.env`，不要写入示例或提交：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

验证码密钥与载荷密钥不要复用认证SECRET_KEY。替换密钥会让旧申请或待投递载荷失效，应先处理旧任务再轮换。所有API、dispatcher和worker必须使用同一组配置。

## 部署与启动

先备份数据库，再从backend执行 `alembic upgrade head`，本模块revision为 `f3c4d5e6a7b8`，前置 `e2b3c4d5f6a7`。必须先迁移再启动新API，避免已有自动建表抢先创建新表。迁移会预检 `lower(btrim(email))` 重复值，包括软删除账号；有冲突时停止，不会自动合并用户。降级遇到超过50字符的新邮箱会拒绝有损截断。

虚拟环境使用工作区完整同步，不能在根目录只运行不带成员参数的uv sync：

```bash
uv sync --all-packages --all-extras --locked
cd backend
# 原API启动命令保持不变；下列两个服务分别在独立终端/受监管进程运行
python -m src.modules.email_verification.dispatcher
python -m taskiq worker src.modules.email_verification.worker:broker --workers 1 --max-async-tasks 2 --ack-type when_executed
```

Windows设置 `PYTHONIOENCODING=utf-8` 后运行；生产不用 `--reload`。默认通用Taskiq worker并没有注册本模块任务，不能代替上面的专用入口。推荐由systemd或容器守护分别管理API、邮件dispatcher和邮件worker，不修改原有协同服务。

### 上线配置文件

本地实际凭据只保存在根目录 `.env`，不得复制到可提交的示例。`backend/.env.example` 和本模块的 [邮件增量模板](deployment/email.env.example) 均只保留邮箱、授权码与密钥占位；后者包含全部24项邮件配置及依赖的RabbitMQ、Redis和可信代理参数。`MAIL_SUPPORT_EMAIL`是可选项，留空时不公开任何联系邮箱。

在服务器已有 `.env` 中逐项合并邮件增量，沿用原有数据库、COS、登录密钥和队列账号，**不要用增量文件覆盖整份站点配置**。将所有 `REPLACE_WITH_*` 替换为服务器实际值；无Redis认证时密码留空，可信代理层数按实际网络填写。新环境生成两项独立密钥后，API、dispatcher和worker共同使用，最后再开启 `MAIL_ENABLED=true`。

[Compose增量文件](deployment/compose.email.yml)只新增邮件dispatcher和worker，适用于现有生产配置已定义 `api`、`migrate`、`postgres`、`redis`、`rabbitmq` 的部署目录。它使用与API相同源码及prod构建目标，容器工作目录固定为 `/app`，以保证 `src.modules...` 模块路径可导入；不修改原有默认worker或协同队列。外部数据库/中间件部署需相应调整文件中的网络主机覆盖值。

下面在包含 `docker-compose.yml`、`backend/` 和 `.env` 的生产部署目录执行；第二个Compose文件应随更新后的后端代码一起复制。先备份数据库、检查占位和配置，再运行迁移、启动API及邮件进程：

```bash
# 先检查服务器配置，命令不输出展开后的凭据。
docker compose -f docker-compose.yml -f backend/src/modules/email_verification/deployment/compose.email.yml --profile email config --quiet

# 仅在完成数据库备份后执行迁移；已有迁移服务要求显式生产确认。
docker compose -f docker-compose.yml -f backend/src/modules/email_verification/deployment/compose.email.yml run --rm migrate

# 初次上线构建更新后的源码，使用专用邮件profile启动两个进程。
docker compose -f docker-compose.yml -f backend/src/modules/email_verification/deployment/compose.email.yml --profile email up -d --build api email-dispatcher email-worker

docker compose -f docker-compose.yml -f backend/src/modules/email_verification/deployment/compose.email.yml --profile email ps
```

本地手动运行继续使用上面的Python命令，并按本机网络设置环境变量 `CACHE_REDIS_HOST=localhost`、`RATE_LIMITER_REDIS_HOST=localhost`、`TASKIQ_REDIS_HOST=localhost`、`COLLAB_RABBITMQ_HOST=localhost`。本机HTTP调试可设置 `SESSION_SECURE_COOKIES=false`；线上HTTPS保持true。新增配置不需要更改实际认证策略或旧业务数据。

## API对接

新邮箱接口均需登录。请求头 `X-Expected-User-ID` 应为发起操作时登录账号ID，不能根据后来的Cookie自动替换；POST还需现有 `X-CSRF-Token` 和Session Cookie。缺账号上下文428，换号409并附 `X-Email-Session-Changed: 1`，不能弹窗登录后自动把旧操作重放给另一个账号。

| 方法与路径 | 入参 | 结果 |
|---|---|---|
| `GET /api/v1/email/status` | 无 | 本人email、email_verified、pending申请；禁止缓存 |
| `POST /api/v1/email/binding/request` | `{"email":"name@example.com"}` | 202，request_id/expires_at/retry_after/delivery_status |
| `POST /api/v1/email/binding/confirm` | `{"request_id":"UUID","code":"123456"}` | 200，绑定后的email/email_verified |
| `POST /api/v1/email/unbind/request` | 无 | 202，验证码只寄往当前邮箱 |
| `POST /api/v1/email/unbind/confirm` | 同确认格式 | 200，email=null、email_verified=false |

申请返回 `delivery_status=queued` 表示数据库登记成功，**不代表已发送**；查询status中的pending.delivery_status可见pending/publishing/queued/processing/sent/failed。`retry_after` 单位秒；429同时返回Retry-After。申请无效/过期/重复消费400，非本人/错误用途申请404，邮箱被占用409，参数422，邮件关闭/限流服务不可用503。

绑定、换绑、重发使用同一个request接口。新申请使旧申请及旧待发验证码失效，绑定与解绑也相互撤销；换绑在验证成功前保留原邮箱。请求确认时再次检查数据库唯一性，不能依赖申请时的检查。无法访问原邮箱时可验证新邮箱换绑，不提供绕过验证码的直接清空途径。

注册扩展保留原路径和201：

```json
{
  "account": "exampleuser",
  "password": "请使用你自己的安全密码",
  "confirm_password": "请使用你自己的安全密码",
  "email": "name@example.com"
}
```

邮箱可选；不填写保持旧注册行为。填写时预检查邮箱占用，已绑定则409且不创建账号。创建成功时正式email仍为null、email_verified=false，响应新增email_verification申请信息。用户仍需正常登录后输入验证码，既有注册不自动建立会话。欢迎信与验证码分开发送，没填邮箱的账号在首次验邮成功后补发欢迎信；换绑不重复欢迎。

`PATCH /users/{username}` 只允许原样保留当前邮箱，不再接受实际邮箱更改和email_verified标记。公开 `GET /users/{username}` 仅返回名片；本人详细资料使用 `/users/me`，管理员列表保留受控邮箱字段。旧的未验证邮箱不会被迁移自动标为已认证，OAuth认证流程保持原样。

## 安全与任务状态

- 验证码为安全随机6位数字；数据库只保存绑定申请ID、账号和用途的HMAC，发送所需载荷使用Fernet加密。RabbitMQ只携带任务ID。
- 错误计数在返回400之前持久提交；同一用户行串行化申请和确认，消费一次后不可重用。最终邮箱唯一性由数据库大小写不敏感索引保证，软删除账号的邮箱不自动释放。
- API只提交数据库，不等待队列或SMTP。数据库事务失败整体回滚；队列或SMTP暂不可用时账号和邮件任务已保存，可重试。注册参数和邮箱接口的错误输入不会被全局校验日志原样记录。
- 验证邮件最多3次投递，退避30/120秒；欢迎信最多5次，退避30/120/600/1800秒。SMTP永久错误立即失败；发送限流/Redis不可用时尚未接触SMTP，不消耗投递次数。
- 独立租约恢复发布中、已排队和处理中断的任务，旧租约不能覆盖新状态。SMTP已接受但响应丢失的极端情况仍可能重复投递；固定Message-ID不是外部绝对去重保证。
- 终态清除载荷；队列离线时dispatcher仍清理失效验证码。终态任务元数据保留30天，欢迎任务保留无载荷的去重墓碑，防止旧账号重复欢迎。账号软删除后不再发送待处理邮件。

日志仅使用任务ID、尝试次数和脱敏错误类型，不输出验证码、授权码、AMQP连接串、收件人或邮件正文。排错可在数据库受控查询任务status/error_code/next_attempt_at，不能向用户暴露加密载荷。

## 本地Mailpit与测试

使用官方固定镜像，在本机绑定SMTP/UI端口；这只是捕获服务，不向外部邮箱转发：

```bash
docker run --rm --name cloudatelier-mailpit -p 127.0.0.1:1025:1025 -p 127.0.0.1:8025:8025 axllent/mailpit:v1.27.4
```

仅本地设置 `MAIL_SMTP_HOST=127.0.0.1`、端口1025、USE_TLS/START_TLS=false、ALLOW_INSECURE=true、用户名与密码为空，发件地址使用 `sender@example.com`。其他密钥配置仍必需。浏览器打开 http://127.0.0.1:8025 查看欢迎和验证邮件，生产环境恢复TLS和QQ账号配置。

```bash
cd backend
python -m pytest tests/unit/modules/email_verification tests/integration/api/v1/email_verification -q
python -m ruff check src/modules/email_verification tests/unit/modules/email_verification tests/integration/api/v1/email_verification
python -m mypy src/modules/email_verification
```

集成测试自动创建临时PostgreSQL，实际传输测试还会创建独立Redis、RabbitMQ、Mailpit和worker子进程。仅测试本地捕获地址，不向真实用户发信，不使用开发/生产库。测试结束会清理进程树和临时容器。QQ实发需要用户自行配置授权码和明确测试收件人后再手动验证。
