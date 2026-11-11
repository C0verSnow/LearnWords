# 当前：DeepSeek 香港 TUN 登录迁移

用户已明确改用 DeepSeek，并要求有窗口模式、关闭浏览器沙箱、中国大陆 +86 地区。代码位于 feature/deepseek-tun，main 尚未更改；.env 与 Infisical 的会话对象已改为 deepseek.json / deepseek-profile.tar.gz，SESSION_MODE=profile、MIHOMO_TUN=1。豆包对象保留。

普通窗口 Login 42979256202 已推进到账号安全验证页，页面明确显示 +86，要求短信验证码。发送按钮已点击一次，正在等待站点安全验证加载，尚未确认短信发送成功；保持同一个远端浏览器，不重复发短信。DeepSeek 登录尚未完成，正式会话、跨 Runner 查询、ZIP 和 Telegram 制卡尚未验收。

所有浏览器工作流使用 Xvfb 虚拟屏幕启动普通 Chrome，headless=False、--no-sandbox，不使用额外容器。13 项远端有窗口 Tests 42979249856 全部通过。之前重复填表追加旧值的错误已有同一真实 Chrome 回归先红后绿。本地仅静态检查，没有编译或测试。官方来源和设计比较见 [设计文档](design.md)。

英文登录页没有单独地区下拉或条款复选框，条款为登录即同意；实际账号安全验证页已确认 +86。真实凭据只从 Infisical 经私有一次性指令填写，未写入仓库或公开工作流输入。

以下保留此前豆包与 DeepSeek 网页访问对照历史。

# 豆包香港出口与远端验收

按用户要求从 DeepSeek 回退到 https://www.doubao.com/chat/，继续使用 GitHub Actions。已有私有 `doubao.json` 和 `doubao-profile.tar.gz` 均存在；此前 profile 在新 Runner 恢复过登录，但消息发送被拒绝。香港节点是否可正常登录和查询，以本轮真实 Probe 结果为准。

## 运行顺序

1. `.env` 使用标准 `MIHOMO_SUBSCRIPTION_URL=...`；`.env.example` 仅保留空值示例。订阅同时保存在 Infisical LearnWords/dev，以及既有私有 Supabase bucket 的 `proxy/subscription.json`（`url` 字段），不进入 Git、Actions 输入、artifact 或 Release。
2. Login、Probe、Make cards 安装已有 Python 依赖后运行 `python -m scripts.mihomo`。下载固定版本 mihomo 并校验 SHA-256；只从订阅挑选香港节点，生成配置保存在被忽略的 `.session/mihomo/`。
3. mihomo 仅监听 Runner 回环地址，通过代理访问 Cloudflare trace，实际国家为 HK 才继续；失败不退回直连或其他地区。通过 `GITHUB_ENV` 设置 `BROWSER_PROXY`，DrissionPage 启动 Chrome 时显式设置代理，Supabase、GitHub 和 Telegram 仍按既有网络直连。
4. **Probe Doubao session** 还会在真实 Chrome 内核对 HK 出口，再恢复 ini 与 profile，查询 approach 并解析完整内容。必须恢复登录和真实查询均通过，才能继续制卡。
5. 两个新 Runner 分别通过 Probe 后，运行 **Make cards** 制作一个词，检查公开 Release 的 ZIP、APKG、manifest 与 ZIP 中媒体，再通过 Telegram 验收完整请求链路。Anki 导入和客户端自动播放由用户另机验收。
6. 仅在已有会话失效时，运行 **Login Doubao session** 并通过私有一次性指令登录。同一浏览器等待人工验证码，成功后导出 JSON、关闭 Chrome、再保存 ini 与用户目录，不反复发短信。

## 验收状态

| 项目 | 结果 |
| --- | --- |
| 订阅规范化与私有保存 | 已完成 |
| 已有豆包 JSON 和 profile 对象 | 已确认存在，不代表当前会话仍有效 |
| mihomo 香港真实出口 | 两次独立 Runner 均确认 HK（42970258764、42970493648） |
| Chrome 香港真实出口 | 两次独立 Runner 均确认 HK |
| 两个新 Runner 恢复并查询完整内容 | 登录恢复均通过；发送均失败，后一次只发送 1 次，HTTP 200 内 STREAM_ERROR 710022004 / rate limited，服务端要求 semantic_reasoning 验证 |
| Release ZIP 与 Telegram 结果 | 待测 |
| Anki 客户端导入与发音 | 用户另机验收 |

不搬用 macOS 的 Chrome 目录，不把 ini 单独当作凭据。归档保留 Cookie、Local Storage、IndexedDB 等，排除普通缓存与锁/socket。DeepSeek 对象与账号配置不删除，本轮不再使用。

所有实际进度带 Unix Timestamp 记录到 tasklist.md。按仓库约定不运行本地编译、构建或测试；验证使用已有远端 Tests 和 Probe 工作流。

本轮远端 Tests 42970252921 的 13 项测试通过；清理临时采集后的最终 [Tests 42971075743](https://github.com/C0verSnow/LearnWords/actions/runs/42971075743) 也已通过。真实账户仍需人工处理豆包验证后重新 Probe；验证未通过前，尚无可验收的 Release ZIP，也不继续重复查询或发短信。临时 completion 响应采集已移除，私有诊断已清理。

## TUN 对照（用户恢复后）

Probe 已改为 MIHOMO_TUN=1，开启虚拟网卡、自动路由及 DNS 劫持；Chrome 不使用单独 HTTP 代理。沿用相同香港候选顺序和 profile，只进行一次真实查询。具体结果见 tasklist.md。其余 Login、Make cards 工作流仍维持原代理方式。

本次 [TUN Probe 42972029205](https://github.com/C0verSnow/LearnWords/actions/runs/42972029205) 已完成：TUN 开关、虚拟网卡、无 HTTP 代理的 HK 出口、Chrome HK 出口和 profile 登录检查均通过。只发出一次 completion，HTTP 200 内仍返回 STREAM_ERROR、710022004、rate limited，且要求 semantic_reasoning 验证。TUN 已在工作流收尾阶段停止。本次结果说明开启 TUN 没有解决当前账户的发送拒绝；仍需处理服务端验证，不继续重复发消息或短信。

## DeepSeek 网页访问对照

用户随后指定检查 https://chat.deepseek.com/。在同一 Probe 工作流选择 target=deepseek，复用相同香港 TUN 设置；用全新独立 Chrome 目录依次读取根页面和 /sign_in，记录主文档 HTTP 状态、密码框/聊天框以及 CloudFront/浏览器验证提示。此检查仅访问页面，不读取或提交 DeepSeek 账号密码，不改变豆包制卡入口。页面诊断只保存到现有私有 bucket。

[DeepSeek 访问检查 42972760085](https://github.com/C0verSnow/LearnWords/actions/runs/42972760085) 实测结果：香港 TUN 与 Chrome 出口均通过 HK 检查。首页 `/` 返回 CloudFront 403；`/sign_in` 主文档返回 200，标题为 DeepSeek - Into the Unknown，密码输入框可见，没有检测到浏览器挑战页。账号登录和对话仍未测试，不能将登录页可打开记为登录成功。TUN 对照代码的远端 Tests 42972022866 第 2 次运行已通过，首次失败在 Chrome 连接阶段；未为此增加代码或本地测试。
