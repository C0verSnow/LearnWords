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
