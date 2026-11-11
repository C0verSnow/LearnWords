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
| mihomo 香港真实出口 | 待远端 Probe |
| Chrome 香港真实出口 | 待远端 Probe |
| 两个新 Runner 恢复并查询完整内容 | 待远端 Probe |
| Release ZIP 与 Telegram 结果 | 待测 |
| Anki 客户端导入与发音 | 用户另机验收 |

不搬用 macOS 的 Chrome 目录，不把 ini 单独当作凭据。归档保留 Cookie、Local Storage、IndexedDB 等，排除普通缓存与锁/socket。DeepSeek 对象与账号配置不删除，本轮不再使用。

所有实际进度带 Unix Timestamp 记录到 tasklist.md。按仓库约定不运行本地编译、构建或测试；验证使用已有远端 Tests 和 Probe 工作流。
