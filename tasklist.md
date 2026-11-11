# 本文档为4象限的任务清单，全文书写大白话

## 想做：
- [1794324618] Supabase 控制台提示 legacy API key 将于 2027 年初退役；当前按仓库既有 service_role 配置上线，后续需要按官方迁移说明改为新版 secret key，不能直接把新版 key 填入当前 Bearer 头：https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys 。
- [1794301047] 完成 issue #1：通过 Telegram 发起任务，在 GitHub Actions 操作豆包，制作并发布带音频的 Anki 卡包。

## 做完：
- [1794357066] 修复后远端 Tests 42931729556 已通过；同一个富文本提交回归场景在旧实现 42931442595 失败、改为点击发送按钮后通过，未进行本地编译或测试。真实豆包 Probe 42931734797 继续验证中。
- [1794325831] Telegram 真实私聊 /start 已收到 Webhook 帮助回复；/status 经过 Vercel 查询 GitHub 后正常回复当前聊天还没有制卡任务。
- [1794325668] Vercel Webhook 已部署至 https://learnwords-kohl.vercel.app/api/telegram；远端鉴权检查错误密钥返回 403、正确密钥返回 200；Telegram setWebhook 已成功并通过 getWebhookInfo 核对目标地址。选择器修正提交 9863153 已推送 main。
- [1794325493] 已在真实豆包页面查询 approach 并得到完整 JSON；通过 Chrome Application 面板导出 29 个 Cookie、33 项 Local Storage、1 项 Session Storage，写入被忽略的 .session/doubao.json，并上传私有 Supabase 对象后回读核对一致；尚未证明跨 Runner 可恢复。
- [1794324795] Supabase 两项组织密钥已在页面确认，LEARNWORDS_ENV 完整备份已再次同步并确认保存；组织密钥全部只授权 LearnWords。Vercel 的本人验证页已留给用户，尚未完成部署；豆包登录会话还未导出或验证跨 Runner 恢复。
- [1794324581] 已保存 LearnWords 的 SUPABASE_URL 与 service_role 到 .env 和 Infisical；已创建并通过 API 核对 browser-sessions 为私有 bucket。尚未上传豆包会话。
- [1794324503] 用户已创建独立 Supabase LearnWords 项目，项目标识 ocoekippsxcwlihlguiy，区域由控制台 Auto 选择为东京；已核对项目 Healthy 并保存项目 URL。Vercel 已按 Other 预设提交部署，七项 Webhook 环境变量均为敏感值，不包含 Supabase 会话密钥。
- [1794324384] main 合并后远端 Tests 已通过：https://github.com/C0verSnow/LearnWords/actions/runs/42843460973 。LEARNWORDS_ENV 组织备份已更新包含新 GitHub token，单仓库访问范围未变。
- [1794324330] 已在 C0verSnow 组织保存 LEARNWORDS_GITHUB_TOKEN，页面确认保存成功，访问范围仅 LearnWords；GitHub 保留 GITHUB_ 前缀，所以组织密钥使用此项目专用名称。
- [1794324053] 已按用户提交前确认生成 LearnWords 专用 GitHub token；仅限本仓库、Actions/Contents 读写，2026-12-10 到期；已保存 .env 和 Infisical，并通过仓库只读请求核对 token 可用，尚未做写入权限实测。
- [1794322613] 按用户明确授权，已合并 PR #2 至 main；合并提交 f4353439ed4691dc64ecbf2ba967667eef41da0d，GitHub 返回合并成功。
- [1794322440] 已复核三项组织密钥全部保存成功，且仅 LearnWords 可访问；TELEGRAM_ALLOWED_USER_IDS 和 TELEGRAM_CHAT_ID 已保存到 Infisical。
- [1794322440] 本次已在 GitHub 检索到 Infisical 官方项目及其许可证，并查阅官方 API 和 GitHub token 权限文档；本次配置工作没有引入新实现或复制第三方代码。
- [1794322305] 已在 C0verSnow 组织新增 LEARNWORDS_ENV 完整配置备份、TELEGRAM_BOT_TOKEN、TELEGRAM_CHAT_ID 三项 Actions Secret，访问范围均只选 LearnWords；已通过页面确认前两项保存，聊天 ID 正在复核。
- [1794322027] 按用户要求通过 BotFather 新建 @C0verSnow_LearnWords_bot；已保存 token 到 .env 和 Infisical，调用 Telegram getMe 核对机器人身份并设置四项命令菜单，token 没有输出。
- [1794321823] 已把六项可确定的运行默认配置和随机生成的 Telegram Webhook 校验密钥保存至 Infisical LearnWords/dev 根目录，并同步到本仓库被忽略的 .env；未覆盖已有密钥，未写入未知账号的占位值。
- [1794321682] 已恢复 Chrome 接管；确认 Infisical LearnWords 的 dev 根目录为空，仓库 .env 只有六项 Infisical 连接配置；用户确认组织密钥目标为 GitHub 的 C0verSnow。
- [1794321682] 已核对 PR #2 仍待 review、没有合并；其最新提交的远端 Tests 已通过：https://github.com/C0verSnow/LearnWords/actions/runs/42789073826 。
- [1794302078] 修正后的远端 Tests 再次通过：12 个测试全部通过，含真实 Chrome 测试页、APKG 音频、HTTP Webhook、发布重跑及缺失交付记录恢复：https://github.com/C0verSnow/LearnWords/actions/runs/42788782351 。
- [1794302078] 已更新 PR #2 的实现说明、测试证据和未做的真实账号验收项；按 issue 原文要求关闭 issue #1，PR 保持打开等用户 review，没有合并。
- [1794301951] 已建 PR #2 等用户 review，没有合并。首轮远端 Tests 通过，12 个测试通过：https://github.com/C0verSnow/LearnWords/actions/runs/42788383796 。
- [1794301951] 修正重跑后残留旧错误和公开 Release 后记录缺失的恢复行为，补充测试；准备运行最终远端 CI。
- [1794301783] 完成 Webhook、持久化请求去重、选词、豆包接口、会话实验工具、双口音 TTS、APKG/ZIP、Release 和检查点恢复代码。
- [1794301783] 检索并比较 DrissionPage、Playwright、genanki、eSpeak NG，记录维护情况、许可和设计取舍到 docs/design.md。
- [1794301783] 用户确认尚无账号配置，先交付代码和配置说明；真实豆包恢复和部署联调没有做，文档不声称已经验证。
- [1794301047] 同步了只有 README 的远端仓库，读完 issue 和补充讨论，建立 feature 分支。

## 没做：
- [1794322384] 当前仍缺 Webhook 专用 GitHub 凭据、Supabase 项目选择及会话对象、Vercel 部署与真实制卡验收；PR #2 原先要求等 review，已向用户询问是否合并。豆包已由用户完成网页登录，但跨 Runner 恢复没有验证。
- [1794302078] 用户尚无账号配置，本次未部署 Vercel/Telegram/Supabase，未验证豆包线上选择器、跨 Runner 登录恢复或 Anki 客户端导入；README 和 docs/session-research.md 已列出配置与验收步骤。
- [1794301047] 按约定不做本地构建、编译或会触发编译的验证；远端测试和真实登录实验另行记录。

## 在做：
- [1794358871] 用户确认收到短信，私有回读也确认已发送并进入验证码页。实际验证码 input 的 placeholder 为空，原定位找不到导致 Login 42935378844 退出；已按实际页面改为可见输入框，并让等待循环持续检查登录成功。验证码不记录，需重新保留远端浏览器后完成登录。
- [1794358646] 已在远端填手机号、勾选登录协议并点击一次下一步，但页面仍停在手机号表单，未确认短信发送。先停止这一轮，增加私有页面提示和输入长度回读，查清原因，不让用户先发验证码、不盲目重发。
- [1794358502] 远端 Login 42934780799 已通过 ini 启动并读到手机号表单、下一步和未勾选协议框；Tests 42934785734 全部通过。新增私有 Supabase 单次指令通道，同一个 Runner 保留浏览器等待验证码，指令读取后删除，不公开手机号或验证码。已实测缺失对象返回 HTTP 400、内部状态 404，按真实响应处理轮询。
- [1794358289] 用户明确改为远端 DrissionPage 手机号登录；按官方 ini 保存与加载接口复用远端 Chrome 启动配置，先只读检查登录表单，再按页面实际要求发短信。手机号和验证码不写入代码、公开输入或日志；清理前轮临时诊断。
- [1794357550] web_storage 模式 Probe 42932615012 也在登录检查失败。继续用最小只读统计区分会话失效与账户选择器误判：只记录全局头像、账户菜单、登录按钮数量与 HTML 长度，不输出网页或会话内容。
- [1794357359] Probe 42932161413 在登录恢复检查就失败，尚未进入发送步骤，说明单独 Cookie 的跨 Runner 恢复不稳定。按既有会话实验步骤只把 SESSION_MODE 切到 web_storage，已通过 API 回读核对并触发相同代码的新 Probe。用户告知电脑连接恢复后，工具重连仍报 native pipe startup failed。
- [1794357122] 真实 Probe 42931734797 点击发送后输入节点被页面重建，30 秒后的临时统计读取旧节点导致 ElementLostError；回归 Tests 已通过。现只修正统计为重新读取当前输入节点，继续确认回答数量和生成标记，不把这次统计异常当作登录失败。
- [1794356945] 远端回归 Tests 42931442595 已按预期变红：12 个测试中只有富文本提交用例失败，错误与真实 Probe 同为等待完整内容超时。现已只把发送操作改为点击真实发送按钮，并增加 send 配置；准备同时跑远端回归与真实豆包 Probe。组织备份更新另有实际阻碍：电脑控制连接不可用，现有 Git 凭据访问组织密钥接口返回 403，不扩大 token 权限。
- [1794356603] Probe 42930649943 已核对真实发送按钮 chat_input_send_button 可见且可用，没有预设的验证、访问受限、发送失败、网络异常或重新登录提示。先把已有真实 Chrome 测试页改为富文本输入、Enter 不提交、按钮提交的回归场景，准备用远端 Tests 证明旧实现失败，再只改发送方式。
- [1794356445] 诊断 Probe 42929926988：输入框 1 个且可见，填入和按 Enter 后均为 271 字，最终仍为 271 字；回答节点为 0、没有生成标记，未进入 JSON 解析。已确认卡在提交消息之前。固定版本源码显示 Enter 映射正常，继续只读取发送控件状态与固定错误提示布尔值；诊断等待缩至 30 秒，加快真实远端复现。
- [1794356109] Cookie 模式远端 Probe 已确认失败：登录检查通过，卡在完整回答等待超时。已读取固定 DrissionPage 4.1.1.4 发布包源码，排除 Enter 默认清空输入的猜测；按四个可证伪方向添加临时统计日志，仅打印节点数量、可见性、文本长度和固定解析错误，不打印网页正文或密钥。远端 Probe 是当前最小真实复现，因仓库禁止本地验证且真实回答需等待，暂保留其等待时限。
- [1794355966] 用户要求继续；恢复检查远端会话探测结果，优先处理实际失败点，继续保持不做本地编译验证。
- [1794325709] 已把仓库 Actions 变量 SESSION_MODE 设为 cookies，并触发 main 的 Probe Doubao session，实验只恢复 Cookie；会话对象含备用网页存储，后续是否启用取决于真实结果。
- [1794325559] 已用 Chrome Elements 面板核对真实页面，修正 config.yaml 的富文本输入框和已登录账户头像选择器；新对话与回答节点的 data-testid 仍与现有配置一致。准备提交配置并用远端 Probe 验证 Cookie 恢复；不做本地构建或测试。
- [1794324691] Supabase 两项组织密钥已保存并在页面复核，仅 LearnWords 可用；Vercel 部署提交后出现 Verify Your Identity，已请用户在页面本人完成验证，尚未取得部署成功结果。
- [1794324084] 已使用新 token 成功触发 main 分支已有 Tests 远端工作流，核对 Actions 写权限；没有运行任何本地构建或测试。Supabase 页面密码未通过强度检查，用户正在自行完成创建。
- [1794323972] 用户已在提交前明确确认生成并保存限定 LearnWords 的 30 天 GitHub token，并告知 Supabase 项目已创建；继续核对页面结果后保存配置。
- [1794322819] GitHub token 表单已限定 LearnWords，权限为 Actions/Contents 读写、Metadata 只读，30 天到期；按浏览器规则等待生成前确认。Supabase 已填 LearnWords 新项目，数据库密码和提交由用户本人完成。
- [1794322556] 用户已明确同意合并 PR #2 并继续上线、为 LearnWords 新建独立 Supabase 项目，并告知已完成 GitHub 本人二次验证；继续配置，仍不进行本地编译验证。
- [1794322440] GitHub 新 token 页面要求本人二次验证，已交给用户完成；继续等待 PR #2 合并决定与 Supabase 项目选择。已完成基础配置和 Bot 保存，尚未部署或声称制卡成功。
- [1794321512] 开始核对真实账号配置和上线缺项；优先读取本仓库 .env，检查浏览器、Infisical 和组织密钥入口，全程不输出密钥，不进行本地编译验证。
- [1794302078] 等待用户 review PR #2，本次代码和配置说明已经交付，没有自动合并。
