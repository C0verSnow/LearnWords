# 豆包登录恢复实验

## 已确认的 API，尚未确认的线上结论

已阅读 DrissionPage 4.1.1.4 发布包源码：`cookies(all_domains=True, all_info=True)` 调用 CDP Storage.getCookies，返回完整 Cookie 字段；默认读取只保留 name/value/domain。它不会自动包含 Local Storage、Session Storage、IndexedDB、Chrome 用户目录、操作系统密钥或服务端风控信息。

`local_storage()` 与 `session_storage()` 分别读取当前源的网页存储，`set_user_data_path()` 指向 Chrome 用户数据目录。三者是不同的状态，不应统称为 Cookie。Session Storage 按标签页隔离，因此生产代码在同一标签页新建聊天，保留可能需要的网页状态。

初次交付时没有真实账号或已部署服务，因此没有把 JSON 会话方案当作已经定型。下面记录后续账号配置与实验进度；本机网页已登录不等于 Ubuntu Runner 可以恢复登录。

## 2026-11-10 真实页面检查

- 已在用户登录的 Chrome 中查询 `approach`，网页返回包含七个所需字段的完整 JSON。
- 通过 Chrome Elements 面板核对，输入框现在是 `chat_input_input` 内的 `contenteditable` 节点，登录头像位于 `data-sidebar-footer-account-menu` 内的 `chat_header_avatar_button`；已修正 `config.yaml`。新对话和回答节点的配置仍能对应真实页面。
- 通过 Chrome Application 面板读取了当前豆包源的 29 个 Cookie、33 项 Local Storage 和 1 项 Session Storage，保存为被忽略的 `.session/doubao.json`。这种导出没有包含 IndexedDB 或整个 Chrome 用户目录。
- 已上传至 LearnWords 独立 Supabase 项目的私有 `browser-sessions/doubao.json` 并回读核对。跨 Ubuntu Runner 的恢复和真实查询仍待远端 Probe 验证。

浏览器操作依据：[Chrome Cookie 面板](https://developer.chrome.com/docs/devtools/application/cookies)。没有读取其他站点的会话，没有把 Cookie 或网页存储写入 Git。

## 待执行步骤

以下命令给人工配置者使用；本次开发没有执行本地安装、浏览器登录或编译验证。Python 依赖为 `requirements-worker.txt`，Chrome 需要使用独立用户目录。

1. 复制 `.env.example` 到 `.env`。在真实页面检查 `config.yaml` 的账户按钮、新建聊天、输入框、回答和生成中选择器。`authenticated` 必须仅在已经登录时出现，不能使用公共输入框替代身份判断。
2. `python -m scripts.session capture --profile .session/profile`：人工登录，确认能够正常查询后按回车，导出 Cookie 与当前源网页存储至 `.session/doubao.json`。脚本不输出内容，不保存截图，目录不会提交。
3. 关闭原浏览器。在 `.env` 设 `SESSION_MODE=cookies`，执行 `python -m scripts.session probe`，使用全新用户目录测试登录和真实消息提交。记录成功或失败，不仅看是否出现输入框。
4. 改为 `SESSION_MODE=web_storage`，再以全新目录执行 probe。比较 Cookie 单独恢复与 Cookie 加两类网页存储的结果。
5. 以 `SESSION_MODE=none` 执行 `python -m scripts.session probe --profile .session/profile`，比较原用户目录重启的结果。此项仅验证同机器目录；不能由此推断 macOS 用户目录能直接搬到 Linux。
6. 若 JSON 恢复可行，将文件上传 Supabase **私有** bucket，配置 Runner secrets 与 SESSION_MODE，在 Actions 手动运行 **Probe Doubao session**，验证全新 Ubuntu 环境中的同一条查询。Supabase 只读取经过实验选择的对象，不建立业务表。
7. 连续使用至少两个新的 Runner，间隔一段时间后重复；记录平均响应耗时、登录是否过期、能否发送新聊天、豆包是否限制访问。遇到验证码或人工校验停止并人工处理。
8. 若只有原用户目录有效，或云 Runner 被拒绝，记录阻碍后另行决定是否需要保存其他状态。当前不实现未经验证的 Chrome 目录跨系统迁移，不声称无人值守已达成。

| 实验 | 登录 | 查询 | 耗时 | 结论 |
| --- | --- | --- | --- | --- |
| 全新进程 + Cookie | 待测 | 待测 | 待测 | 未确认 |
| 全新进程 + Cookie/Local/Session Storage | 待测 | 待测 | 待测 | 未确认 |
| 同机原用户目录重启 | 待测 | 待测 | 待测 | 未确认 |
| Ubuntu Runner 恢复 | 待测 | 待测 | 待测 | 未确认 |
| 第二个新 Runner + 间隔后重试 | 待测 | 待测 | 待测 | 未确认 |

## 上线验收

- Telegram `/make 1` 只创建一个任务，重复的 update_id 不重复排队；无效参数和未授权用户不触发任务。
- Ubuntu Runner 可恢复真实登录，独立聊天返回完整解释；逐词校验，多词失败不丢其他已完成内容。
- 导入真实 APKG：英美 IPA、全部解释字段和音频存在；正面按客户端设置自动播放，离线可用。
- 相同单词的更新卡包在目标 Anki 客户端按导入设置更新，不造成不必要的重复。
- `/make 5 random` 发布 APKG/ZIP/manifest，结果数量与 Telegram 一致；失败任务原号重跑可恢复。
- 发布失败没有新增 generated 记录，已公开 Release 的 Telegram 通知失败不会撤销成果。

实验结果请继续带 Unix Timestamp 记录到 `tasklist.md`。不要将会话 JSON、用户目录、真实登录日志或密钥提交到公开仓库。
