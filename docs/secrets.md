# 密钥放在哪里

共用 Infisical Cloud 的 Example Project，运行配置统一使用 dev。GitHub 组织保存 `INFISICAL_CLIENT_ID`、`INFISICAL_CLIENT_SECRET` 两项共用机器凭证，组织 Variables 保存项目 ID、`INFISICAL_ENVIRONMENT=dev`、`INFISICAL_API_URL=https://app.infisical.com`。本仓库 Secret `INFISICAL_SECRET_PATH` 指向 `/learnwords/github-actions`。目录用来归类，共用机器身份仍能读取项目内其他目录，不代表仓库间权限隔离。

| Infisical dev 目录 | 用途 |
|---|---|
| `/learnwords/github-actions` | 浏览器档案密钥、Supabase、Tailscale、Telegram 通知与生成参数 |
| `/learnwords/vercel` | Webhook 使用的 Telegram 配置、GitHub 触发 PAT 和仓库定位 |
| `/learnwords/legacy` | 旧 DeepSeek、Mihomo 实验配置；当前工作流不加载 |

三个生产工作流先通过复用的 composite action 安装固定版本 CLI，再以组织机器身份读取本仓库目录。程序只把 Runner 所需字段注入后续步骤并遮住日志；认证失败即停止。GitHub 的短期 `github.token` 保持由 Actions 提供，Webhook 的长效 PAT 不进入 Runner。未配置 IPv6 时省略 `TS_EXPECTED_IPV6`，沿用现有可选行为。Supabase、Tailscale、浏览器档案与登录方式继续沿用原实现。

本机 `.env` 只留统一的 Infisical 启动配置，并保持 Git 忽略和 0600 权限。业务密钥在上表对应目录维护，不再把整包 ENV 当组织 Secret 更新。Vercel 运行时配置是否已同步、旧项目是否仍有外部使用者，以本次交付清单为准，不能仅凭目录复制成功当成线上生效。

迁移前的 GitHub 业务密钥先保留给默认分支的旧工作流。合并这次接入后，再删除这几项旧仓库 Secret 和 LearnWords 专属组织 Secret，避免接入期间断供。旧 Infisical 项目留作回退，不继续维护双份。

## 实现依据与验证

已在 GitHub 对比 [Infisical CLI](https://github.com/Infisical/cli) 和 [Infisical Secrets Action](https://github.com/Infisical/secrets-action)。前者是独立二进制，普通代码为 MIT Expat、ee 目录另有许可；后者为 MIT，依赖 JavaScript Action。两者都在维护，CLI 当天有提交和近期问题讨论。本仓库沿用同组织 TGMusic 已验证的官方 CLI 0.45.6、官方 Release SHA-256 与 Universal Auth 流程，不引入另一套密钥工具，不复制第三方实现。CLI 的递归 JSON 会丢掉目录信息，因此迁移必须逐目录读取；空值字段不使用批量文件导入。

手动运行现有 Tests 工作流，会额外执行一次真实 Infisical 注入检查；它不启动业务浏览器、不发送消息，也不恢复或改写登录档案。代码测试只在远端 CI 执行，本地只做静态检查。
