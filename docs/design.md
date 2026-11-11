# 设计与开源参考

2026-11-10 在 GitHub 检索浏览器自动化、Anki 制卡和发音合成实现；没有直接复制第三方项目代码。

| 项目 | 检索时的维护情况 | 依赖与思路 | 已知限制与采用方式 |
| --- | --- | --- | --- |
| [g1879/DrissionPage](https://github.com/g1879/DrissionPage) | 12,568 stars，最近提交 2026-10-27；关闭 issue #709 有回复 | 直接用 CDP 驱动 Chrome，无需匹配 chromedriver；官方有 Cookie、网页存储、独立用户目录 API | 当前 README 是附带非商业限制的自定义条款，不能宣称为 MIT/OSI 许可证。作为 issue 指定的依赖使用，不复制源码；[Chrome 136 连接问题 #556](https://github.com/g1879/DrissionPage/issues/556) 说明独立用户目录必要。核对 PyPI 4.1.1.4 源码中的 API 后固定版本。 |
| [microsoft/playwright-python](https://github.com/microsoft/playwright-python) | 15,094 stars，最近提交 2026-11-10；关闭 issue #3330 有回复，Apache-2.0 | 独立浏览器上下文，显式 storage state，需额外浏览器安装 | 符合活跃和许可要求的比较候选。会话并非只含 Cookie 的思路可借鉴，但本任务明确选用 DrissionPage，不再引入第二套浏览器框架。 |
| [kerrickstaley/genanki](https://github.com/kerrickstaley/genanki) | 2,804 stars，最近提交 2024-12-30；issue #165 在 2026-08-11 有回复，MIT | 固定 Model/Deck ID，稳定 Note GUID，media_files 与原生 sound 字段 | 没有近期代码提交，不算满足全部活跃门槛的新候选；作为 issue 明确要求的成熟依赖使用。借鉴官方媒体与 GUID 设计；Anki 实际更新效果仍需客户端验证。 |
| [espeak-ng/espeak-ng](https://github.com/espeak-ng/espeak-ng) | 7,017 stars，最近提交 2026-11-08，GPL-3.0；近期 issue 有关闭处理 | 外部命令行同时输出 IPA 和 WAV，Actions 通过 Ubuntu 包安装，不依赖云 TTS 密钥 | 满足活跃与明确许可条件；声音机械，多音词与语境可能不符。选择英美两种 voice，来源进入 manifest，不抓取网站发音文件。 |

不把维护不活跃或许可不明的豆包网页脚本当作实现来源。业务存储和会话存储分开：业务只写 `docs/`，Supabase 只读私有会话对象；是否需要、是否足够由实验决定。

网页 UI 可能调整，因此选择器集中在 `config.yaml`。输入、发送、账户按钮、新聊天、生成中和回答这六项需在真实账号页面核对。当前真实页面的富文本框填入后按 Enter 没有提交，远端探测确认发送按钮 `chat_input_send_button` 可见且可用，因此使用明确的发送按钮，不把 Enter 当成提交契约。回答必须对应目标单词且六个解释字段均为非空文本才进入缓存；代码只检查结构，内容事实和例句质量需要人工抽检。

GitHub 请求去重采用 Contents API 创建以 update_id 命名的文件，避免 Vercel 内存去重随实例消失。任务之间按 Actions 队列串行执行。正常处理单词失败与发布失败，不加入推测性竞态锁或额外数据库。

接口依据：

- [DrissionPage 4.x 网页信息](https://www.drissionpage.cn/dp40docs/ChromiumPage/get_page_info/)、[启动配置](https://www.drissionpage.cn/dp40docs/ChromiumPage/browser_opt/)。Cookie 读取 API 不等于整个 Chrome 用户目录导出。
- [genanki 媒体与 GUID 官方说明](https://github.com/kerrickstaley/genanki#media-files)。
- [Vercel Python /api 入口](https://vercel.com/docs/functions/runtimes/python#existing-projects-using-api)：BaseHTTPRequestHandler。
- [GitHub 并发与 queue: max](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)。
- [Telegram Webhook](https://core.telegram.org/bots/api#setwebhook)：secret_token 请求头、message 更新。
- [Supabase 私有对象下载](https://supabase.com/docs/reference/python/storage-from-download)：只在 Runner 下载，不给 Webhook 访问会话的权限。

## ini 与用户目录实验

2026-11-10 再次检索并比较 [microsoft/playwright](https://github.com/microsoft/playwright)（99,802 stars，Apache-2.0，最近提交 2026-11-10，issue #44038 有 5 条讨论）和 [puppeteer/puppeteer](https://github.com/puppeteer/puppeteer)（95,822 stars，Apache-2.0，最近提交 2026-11-10，issue #667 有 19 条讨论且当天更新）。Playwright 使用 `launch_persistent_context(user_data_dir)`，Puppeteer 使用 `userDataDir`；两者都复用浏览器独立目录，分别依赖自身 Python/Node 浏览器驱动与浏览器安装。采用“持久化独立用户目录”的设计，不引入这两套依赖、不复制代码。参考 [Playwright 官方持久上下文说明](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context) 和 [Puppeteer 启动参数](https://pptr.dev/api/puppeteer.launchoptions)。

DrissionPage 的 [ini](https://www.drissionpage.cn/advance/ini/) 只管理启动配置；真正登录状态在 [用户目录](https://www.drissionpage.cn/browser_control/connect_browser/)。现有 JSON 恢复实验在新 Ubuntu Runner 遇到地区限制，用户同意继续验证 ini 加完整用户目录：登录完成先关闭 Chrome，再打包 ini、Cookie 数据库、网页存储等文件，上传已有私有 Supabase；运行时下载解压，在 ini 基础上调整本 Runner 的用户目录与 Chrome 路径。归档不包含进程锁、socket 和符号链接，也不会进入 Git、Release 或 Actions artifact。

这只是同平台新 Runner 的实验，不代表目录跨操作系统可迁移，也不能保证能绕开服务端会话或地区要求。多个实例不能同时使用一个目录，沿用既有串行工作流，不新增锁。目录归档由 Python 标准库 tarfile 生成与读取，不新增依赖。


## 2026-11-11 DeepSeek 网页迁移

用户指定使用 https://chat.deepseek.com/，并保留 ini + 完整用户目录。沿用现有 DrissionPage、私有 Supabase 和串行 Actions，不新增网页 API 代理或浏览器框架，不复制第三方代码。

| 检索项目 | 维护与许可 | 实现与依赖 | 比较结论 |
| --- | --- | --- | --- |
| [cv-superding/dsh-deepseek-web-login](https://github.com/cv-superding/dsh-deepseek-web-login) | 372 stars，2026-11-04 有提交，Apache-2.0；[issue #23](https://github.com/cv-superding/dsh-deepseek-web-login/issues/23) 有维护者回复 | Node/Electron 登录捕获、独立浏览器 profile、私有接口与 SSE 适配 | 借鉴独立 profile 的边界；其私有接口方案有账号异常反馈，不采用请求重放或挑战求解实现。 |
| [ForgetMeAI/FreeDeepseekAPI](https://github.com/ForgetMeAI/FreeDeepseekAPI) | 483 stars，2026-10-07 有提交，MIT；尚未核实 issue 响应，不纳入最终采用候选 | Node 代理、独立 Chrome 登录目录、导出认证文件 | 用于对比登录数据与运行环境的差异；不引入代理或其代码。 |
| [microsoft/playwright](https://github.com/microsoft/playwright) | 99,813 stars，2026-11-11 有提交，Apache-2.0；已有活跃 issue 记录见上文 | 持久上下文，额外 Playwright 与浏览器依赖 | 继续借鉴关闭浏览器后保存独立目录的设计，用既有 DrissionPage 实现。 |
| [CloakHQ/cloakbrowser](https://github.com/CloakHQ/cloakbrowser) | 32,825 stars，2026-11-10 有提交；仓库包装器 MIT | 修改后的 Chromium、Playwright/Puppeteer 包装器、约 200 MB 下载；当前 README 表明每次启动需要许可证 key，支持持久用户目录 | 用户指定的条件性备选。现不引入；若实际遇到自动化检测，再核实 DrissionPage 二进制接入、浏览器发行许可与已有 key。README 的检测通过宣传不等于 DeepSeek 已验证可用。 |

新会话对象默认 `deepseek-profile.tar.gz`，不覆盖豆包对象。登录成功后关闭 Chrome，再归档 chrome.ini 和 profile 下的 Cookie、Local Storage、IndexedDB 等文件；仍排除普通网页缓存与运行中锁/socket。账号密码由 Infisical 读取，兼容用户现有键 `DEEPSEEK_USRE`，通过现有私有一次性指令通道填入远端网页，不进入公开 Actions 输入或日志。图形验证码保留同一个浏览器等待处理，不自动循环尝试。

## 2026-11-11 回退豆包并使用香港 mihomo

本次在 GitHub 检索并核对 [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo)（35,669 stars，2026-11-11 有提交，当前仓库声明 MIT；近期关闭 issue #3409、#3408 有讨论）与 [clash-verge-rev/clash-verge-rev](https://github.com/clash-verge-rev/clash-verge-rev)（157,705 stars，GPL-3.0，2026-11-11 有提交，近期发布 v2.5.10，2026-11-10 的 issue #8618、#8616 有回复）。后者是 Rust/Tauri 桌面壳并使用 mihomo 内核，Runner 无需桌面管理器，因此直接用官方 mihomo 发布二进制，不引入 GUI 或其他代理框架，不复制第三方代码。

参考 [mihomo 配置](https://wiki.metacubex.one/en/config/general/)、[代理组](https://wiki.metacubex.one/en/config/proxy-groups/) 与 [DrissionPage 浏览器启动代理](https://www.drissionpage.cn/browser_control/browser_options/)。采用回环 HTTP/mixed 代理和固定 select 组：启动时筛选香港节点，逐个验证真实 HK 出口后保持当前节点，不按测速自动切换。只让 Chrome 使用代理，不设置全局 HTTP_PROXY，也不安装 TUN 或改 Runner 路由。节点显示香港不代表实际出口为香港，所以以 Cloudflare trace 国家检查为准；Chrome 再独立核对其真实出口。香港出口可用不等于豆包一定接受，仍以真实页面查询为准。

固定 mihomo v1.19.33 的 linux-amd64-compatible 压缩包，SHA-256 取自官方 Release asset digest。订阅需为含 proxies 的 Clash/mihomo YAML；不实现其他订阅格式转换。订阅与节点配置沿用现有私有 Supabase 通道及 .session 忽略目录，不扩展 GitHub token 权限。控制接口与 mixed 端口只监听 127.0.0.1，进程随一次性 Runner 结束销毁。

回退时恢复了原豆包按钮提交方式和已有“发送失败只发一次，停止后续单词”的远端浏览器回归。页面出现明确失败图标时，沿用现有停止流程，不连续重试被拒绝的消息。

## 2026-11-11 单次 TUN 对照

用户明确要求开启 TUN 后再测试一次。继续使用前文已比较过的 mihomo 与同一份香港订阅，在 GitHub 检索了 [官方 TUN 文档源码](https://github.com/MetaCubeX/Meta-Docs/blob/main/docs/config/inbound/tun.en.md)，核对 [TUN 配置](https://wiki.metacubex.one/en/config/inbound/tun/) 和 [DNS 配置](https://wiki.metacubex.one/en/config/dns/)。对比 system/mixed 与 gvisor：前者使用内核 TCP 栈，后者用用户态协议栈；本轮选择已有二进制内置的 gvisor，不引入依赖。参考 [system/IPv6 DNS 问题 #2560](https://github.com/MetaCubeX/mihomo/issues/2560) 和 [systemd-resolved 问题 #2907](https://github.com/MetaCubeX/mihomo/issues/2907)，采用官方 auto-route、auto-redirect、strict-route 与 DNS 劫持配置，不增加系统 DNS 管理器的额外适配。

仅 Probe 工作流设置 MIHOMO_TUN=1；Login 与 Make cards 仍沿用此前 HTTP 代理，避免本次对照扩大到生产流程。mihomo 通过 Runner 自带 sudo 获得创建虚拟网卡和配置路由的权限，启用 LearnWords TUN 网卡，DNS 使用 fake-ip、respect-rules 与独立节点域名解析。Chrome 显式传入 --no-proxy-server，不设置 BROWSER_PROXY。先核对控制接口实际 tun.enable、虚拟网卡存在，以及忽略 HTTP 代理环境变量时出口为 HK，再在 Chrome 内独立检查 HK，最后恢复同一 profile 并只发送一次查询。

失败时私有诊断只保存 completion 的 HTTP 状态和固定错误布尔值，不保存原始响应或验证凭据。无论成功失败，Probe 都停止 root 运行的 mihomo，再执行 Runner 清理。此项用于比较 TUN 与此前 HTTP 代理，不代表 TUN 能解除豆包的账号验证要求。
