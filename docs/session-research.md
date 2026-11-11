# DeepSeek 登录恢复与远端验收

按用户要求迁移至 https://chat.deepseek.com/，正式方案为 **ini + 完整用户目录**。此前豆包已恢复登录，但真实 completion 返回 `710022004 / rate limited` 和验证要求，未生成首个 ZIP；豆包实验历史保留在 tasklist.md，不把其结果当作 DeepSeek 已通过的证据。

## 会话保存

1. 运行远端 **Login DeepSeek session**，输入仅为随机 login_id。账号来自 Infisical LearnWords/dev，当前键名为 `DEEPSEEK_USRE` 与 `DEEPSEEK_PASSWORD`。
2. 通过已有私有 Supabase 一次性指令通道填入账号密码并提交。状态与页面截图仅保存在同一私有 bucket。遇到图形验证保留浏览器，处理后继续，不重复启动登录或连续提交。
3. 已登录标记必须是账户控件，不能仅凭输入框判断。登录成功后关闭 Chrome，待数据库写回，再归档 `chrome.ini` 和 `profile/`。
4. 归档保存为私有 `browser-sessions/deepseek-profile.tar.gz`。包含 Cookie、Local Storage、IndexedDB 等用户数据；普通缓存和运行锁/socket 不属于需要恢复的登录数据，继续排除以符合存储上传大小限制。
5. **Probe DeepSeek session** 使用新 Ubuntu Runner 下载归档，以 ini 加载参数，并将用户目录路径和 Chrome 路径改为当前 Runner 的实际位置。必须真实查询 approach 并解析完整 JSON，才算恢复与查询通过。
6. 第二个新 Runner 重复探测，再用 **Make cards** 制作一个词并检查 Release ZIP。Telegram、Vercel 和 Release 流程沿用现有实现；Anki 导入由用户在另一台电脑完成。

不将 macOS 的 Chrome 目录搬到 Linux，不把 ini 单独当作登录凭据。会话、账号密码和截图不进入 Git、公开 Release 或 Actions artifact。首次迁移验收在 feature 分支运行，生产分支仍需 review 后合并。

## 待验收

| 项目 | 结果 |
| --- | --- |
| Infisical 账号读取 | 已读取，不输出值 |
| DeepSeek 实际页面选择器 | 已检查本机 textarea 与账户控件；远端仍需核对 |
| 远端账号密码登录与图形验证 | 待测 |
| 关闭 Chrome 后保存 ini 与用户目录 | 待测 |
| 两个新 Runner 恢复并查询完整内容 | 待测 |
| 真实 Release ZIP 与 Telegram 结果 | 待测 |
| Anki 客户端导入与发音 | 用户另机验收 |

所有实际进度带 Unix Timestamp 记录到 tasklist.md。按仓库约定不运行本地编译、构建或测试；仅做静态/差异检查，验证使用已有远端 Tests 和 Probe 工作流。
