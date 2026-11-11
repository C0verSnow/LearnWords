# LearnWords

通过 Telegram 指定数量，在 GitHub Actions 用 DrissionPage 操作DeepSeek，生成带英美音标和发音的 Anki 卡包，然后发布到 GitHub Releases。只负责制卡，不记录学习进度、不安排复习。

```text
Telegram /make 20 random
  → Vercel /api/telegram（鉴权、参数检查、持久化请求去重）
  → GitHub Actions（选词、DeepSeek、音标和音频、Anki、发布）
  → Release（APKG、ZIP、manifest）→ Telegram 结果通知
```

## 当前交付边界

Telegram、Vercel Webhook 和私有 Supabase 已配置。现按用户要求使用 DeepSeek、有窗口 Chrome、关闭浏览器沙箱和香港 TUN。账号已从 Infisical 私有填写，真实安全验证页已确认 +86，正在完成短信验证；正式登录会话、跨 Runner 恢复、内容生成和首个 ZIP 尚未完成。有窗口的 13 项远端 Tests 已通过。结果记录在 tasklist.md；Anki 客户端由用户另机验收。详见 [会话实验](docs/session-research.md)。

## 指令

| 命令 | 用途 |
| --- | --- |
| `/make 20` 或 `/make 20 next` | 顺序选择未成功交付的单词 |
| `/make 20 random` | 随机选词 |
| `/status` | 当前私聊最近任务的 Actions 状态与链接 |
| `/release` | 仓库最新公开 Release |
| `/help` | 帮助 |

只接受 `TELEGRAM_ALLOWED_USER_IDS` 中的用户私聊。默认每次最多 100 词，可通过 `MAX_CARDS` 调低。少于请求数量时按剩余数量处理，并报告缺额。单词支持英文字母、内部短横线或撇号；空行、无效行和重复行会被忽略。

## 配置顺序

1. 合并 PR 后，在 Actions 的 **Tests** 中确认远端测试通过。制卡工作流保留手动入口，没有每日定时器。
2. 修改 `docs/words/vocabulary.txt`，一行一个单词。当前五个单词仅为起步样例。
3. 按 [会话实验](docs/session-research.md) 人工登录并测试新的浏览器进程；根据真实页面更新 `config.yaml` 的选择器。样例中的 `data-testid` 是待核对的配置，不是已经验证的线上页面契约。
4. 在 Supabase 建立私有 Storage bucket `browser-sessions`。JSON 模式使用 `deepseek.json`；`profile` 模式使用 `deepseek-profile.tar.gz`，由远端 **Login DeepSeek session** 登录成功并关闭 Chrome 后保存 ini 和独立用户目录。不用建业务表；不能只上传 ini，或直接搬用 macOS 的 Chrome 目录。
5. 配置下表的 Actions secrets/variables，手动执行 **Probe DeepSeek session**。确认 Ubuntu Runner 可以恢复登录并发出查询后，先手动运行 **Make cards**，数量填 `1`。
6. 导入生成的 APKG，检查字段、英美发音和自动播放。确认后再部署 Webhook。
7. 用 BotFather 创建 Telegram Bot；在 Vercel 导入本仓库，Framework 选 Other，根目录为仓库根目录，不设置前端构建命令。入口为 `api/telegram.py`，使用 Python 3.12。
8. 配置 Vercel 环境变量并重新部署；将 Telegram Webhook 注册为 `https://你的域名/api/telegram`，`secret_token` 与 `TELEGRAM_WEBHOOK_SECRET` 一致，`allowed_updates` 只含 `message`。可用 `python -m scripts.webhook https://你的域名/api/telegram` 读取 `.env` 完成注册，脚本不会打印 token。
9. 私聊发送 `/make 1`，确认受理、Actions、Release 和最终通知，再测试 `/make 5 random`、无效数量和重复更新。

### 环境变量

仓库 `.env.example` 可复制为 `.env`；代码优先读取当前仓库 `.env`，已存在的环境变量优先，不要提交真实会话或密钥。

| 名称 | Vercel | Actions | 说明 |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | 必填 | Secret，通知用 | Bot token |
| `TELEGRAM_WEBHOOK_SECRET` | 必填 | 不需要 | 注册 Webhook 的 secret_token |
| `TELEGRAM_ALLOWED_USER_IDS` | 必填 | 不需要 | 用户数字 ID，逗号分隔 |
| `GITHUB_TOKEN` | 必填 | 自动使用 github.token | Vercel 使用 fine-grained PAT，限定本仓库，Actions 与 Contents 均需 write |
| `GITHUB_REPOSITORY` | `C0verSnow/LearnWords` | 自动 | 仓库名 |
| `GITHUB_REF` | `main` | 自动使用工作流分支 | Webhook 触发的分支；必须已有工作流 |
| `MAX_CARDS` | 可选，默认 100 | Variable，默认 100 | 两端保持一致，范围 1–100 |
| `TELEGRAM_CHAT_ID` | 不需要 | Secret，可选 | 手动触发时的通知聊天；Telegram 触发自动传入 |
| `SESSION_MODE` | 不需要 | Variable，默认 profile | 实验确认后选择 cookies、web_storage 或 profile |
| `SUPABASE_URL` | 不需要 | Secret | 私有会话对象所在项目 |
| `SUPABASE_SERVICE_ROLE_KEY` | 不需要 | Secret | 仅 Runner 读写私有会话对象 |
| `SUPABASE_SESSION_BUCKET` | 不需要 | Variable，可选 | 默认 browser-sessions |
| `SUPABASE_SESSION_OBJECT` | 不需要 | 工作流固定 | deepseek.json，避免覆盖豆包对象 |
| `SUPABASE_PROFILE_OBJECT` | 不需要 | 工作流固定 | deepseek-profile.tar.gz，包含 ini 与浏览器用户目录 |
| `MIHOMO_SUBSCRIPTION_URL` | 不需要 | 私有配置 | Clash/mihomo YAML 订阅；本机保存在 .env，Runner 从同一私有 bucket 的 proxy/subscription.json 读取，不使用公开工作流输入 |
| `BROWSER_PROXY` | 不需要 | 启动脚本自动设置 | http://127.0.0.1:7890，仅 Chrome 走香港节点 |
| `CHROME_PATH` | 不需要 | 工作流自动发现 | Runner 自带 Chrome；本机实验可手动指定 |

GitHub 必须允许 Actions 写 Contents；若分支保护阻止机器人提交 `docs/`，先为这个自动化选择允许写入的数据分支，并让 `GITHUB_REF` 与手动运行的分支一致。不要在有人工改动但未提交的目录运行制卡程序。

## 数据与状态

```text
docs/words/vocabulary.txt      词表
docs/requests/tg-*.json        Telegram 请求去重凭证
docs/explanations/<word>.json  已校验的DeepSeek解释，中断后复用
docs/records/generated.json   已发布卡包的单词记录（首次成功后自动生成）
docs/manifests/<task>.json     数量、失败原因、阶段、Release 地址
output/<task>/                APKG、ZIP、音频和清单，不进 Git
```

任务阶段依次为 `selected`、`content_generated`、`packaged`、`published`。`failed` 表示任务失败；`delivery_record_failed` 表示已获得 Release 地址但提交交付记录失败；`no_available_words` 表示没有可制卡词。部分单词失败仍发布完整成功的卡片，并明确报告失败和词表缺额。没有完整音标或任一发音文件的词不会算成功。

先保存生成内容和打包检查点，再创建草稿 Release，全部资源上传后才转为公开，最后写成功记录。仅已发布的词会在新任务中被排除。Release 内的清单和 ZIP 清单记录**打包时**的 `packaged` 阶段；`docs/manifests/` 是后续发布结果的依据。

工作流使用 `concurrency` 的 `queue: max` 串行写制卡记录，最多等待 100 个任务；超出平台队列上限的任务会被取消，可通过 `/status` 查看。Webhook 写入独立请求文件，Runner 推送前 rebase 保留这些请求。

## 重试与恢复

- 每个词最多尝试两次，可在 `config.yaml` 调整为 1–3 次。登录失效立即停止后续DeepSeek请求，不反复登录。
- 已保存的解释会被复用，发音重新生成，卡片 GUID 仅由系统版本与单词决定。模型和牌组 ID 固定，重导入时须核对 Anki 的更新选项。
- 如果 Release 已公开但最终记录未提交，原任务重跑会按打包检查点补写交付记录，保持已发布单词清单，不扩大这次卡包的成功数量。
- 在 Actions 重跑失败任务，或手动运行 **Make cards**，填写原 `request_id`，即可复用原选词清单。已发布任务重跑只反馈原链接，不重建 Release。
- 同一个任务号不会补做已经发布的部分失败词；需要补做时发起新任务，未交付词仍可选。改 count/mode 不会改变已经创建的任务；要新选词请使用新任务号。
- APKG 或 Release 失败时保留成功解释；Release 上传失败保留草稿，重跑时重新上传。已公开的同任务 Release 保持原样。
- 如果仓库检查点推送失败，从 Actions 的 `learnword-<run_id>` artifact 取回 `docs/` 结果提交后，再重跑原任务。Artifact 保留 14 天；不会包含会话文件或浏览器用户目录。
- Webhook 先落请求凭证，再触发工作流。若 GitHub 未确认触发，Bot 会返回任务号；用 `/status` 确认后手动补跑该任务号。凭证会保留，避免网络超时后 Telegram 重投导致重复排队；服务在这两步之间中断也按此方法恢复。
- Telegram 通知失败不撤回 Release；可在 Actions 和 `/release` 查看成果。

## 音标与媒体

使用独立的 [eSpeak NG](https://github.com/espeak-ng/espeak-ng) 引擎生成 `en-gb`、`en-us` IPA 和 WAV。采用合成发音，避免转发来源和再分发许可不明确的词典录音；这是 TTS 音标和发音，不能宣称是真人词典数据，多音词仍应人工核对。来源写入任务清单和 ZIP 说明。

卡片包含 Word、IPA_UK、IPA_US、Audio_UK、Audio_US、Intuition、Meaning、Usage、Examples、Comparison、MemoryTip。媒体通过 Anki 原生 `[sound:文件名]` 引用并随 APKG 打包；正面包含两种口音，是否自动播放取决于客户端设置，不注入 JavaScript 播放器。HTML 字段会转义DeepSeek文本。

## 验证

按仓库约定，不执行本地构建、编译或测试。远端 **Tests** 使用真实 eSpeak NG、genanki、SQLite 和 ZIP 检查双口音媒体、稳定 GUID、字段转义、词表选词，并通过本地 HTTP 测试服务检查 GitHub 请求去重、发布失败、恢复和真实 Git 检查点。浏览器测试在 Runner 的 Chrome 上操作测试页，不使用DeepSeek账号。

真实上线验收清单在 [会话实验](docs/session-research.md)。设计比较和开源来源见 [参考设计](docs/design.md)。
