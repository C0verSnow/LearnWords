# 豆包大陆出口部署与故障处理

## 当前方案

GitHub-hosted Ubuntu 24.04 Runner 执行 Python、Xvfb、有头 Chromium 和 DrissionPage。大陆服务器只运行 Tailscale Exit Node，普通网络流量由 tailscale0 和 Tailscale 路由转发，不在 Chrome 配置 HTTP/SOCKS 代理，不再启动 mihomo。

当前服务器为 `192.168.1.245`，Tailscale IPv4 为 `100.124.220.89`。这两个地址用途不同，Runner 使用后者。服务器处于 NAT 后不影响方案，Tailscale 可直连或经 DERP 中继；没有承诺带宽与延迟。

OpenWrt `192.168.1.1` 已有 OpenClash。服务器原先访问 Cloudflare 的出口为日本，按服务器 Wi-Fi MAC 加入 OpenClash 自带绕过列表后，同一查询返回 CN。此项同时排除该设备的 DNS 劫持，其余设备继续沿用原分流。OpenWrt 不安装 Tailscale，原因见 [评估](tailscale-openwrt-assessment.md)。

## 从零部署

1. 在中国大陆 Linux 服务器执行 `sudo bash scripts/setup_exit_node.sh`。脚本只在缺少 Tailscale 时从官方源安装，持久开启 IPv4/IPv6 转发并广播出口。首次登录需先执行 `sudo tailscale up` 并完成官方登录。
2. 检查脚本的公网 IPv4 和 `loc=CN`。若仍是境外出口，先检查上游路由器代理和 DNS 劫持，不能把物理位置当作实际出口。
3. 在 Tailscale Machines 找到该服务器，批准 **Use as exit node**。服务器只提供出口，不需要广播家中网段，也不需要开放内网 SSH 给 CI。
4. 为 Runner 定义 `tag:learnwords-ci`，标签所有者为管理员。对该来源只授权 `autogroup:internet`；现有的 `src: ["*"]` 全网放行规则会覆盖这个限制，必须按现有用户及旧标签收窄，保留其他设备权限。新 Runner 不应能访问 `100.124.220.89:22` 或路由器管理口。
5. 创建 LearnWords 专用 OAuth，只选 **Auth Keys / Write**，并限定 `tag:learnwords-ci`。不要借用其他项目的凭据。官方 GitHub Action 创建临时节点，工作流结束后退出并清理节点。
6. 保存下表配置到本仓库 `.env`、私有 Infisical 和 GitHub Actions；不要把真实值写入仓库、工作流输入、Issue 或日志。`BROWSER_PROFILE_KEY` 是 `cryptography.fernet.Fernet.generate_key()` 生成的 URL-safe base64 32 字节随机密钥；丢失就无法解密已有归档，必须私有备份。
7. 手动运行 **Tests**，只在远端执行测试。随后运行 **Probe browser access and session**，先选择 `network`，确认 TUN、IPv4/IPv6、DNS、实际出口及豆包 HTTP。
8. 对现有未加密对象，只运行一次 Probe 的 `migrate`。它读取旧 `doubao-profile.tar.gz`，加密到独立对象，下载解密回读比对；不会打开浏览器，也不会重新发送短信。
9. 运行 Probe 的 `session`：新 Runner 解密完整用户目录，启动有头 Chrome，核对 Chrome 出口、登录、发送一次 approach 并解析完整内容。关闭后加密保存更新。应再用一个新 Runner 复验。
10. 只有会话确实失效时才运行 **Login Doubao session**。`login_id` 使用 UUID，不含手机号或验证码。通过已有私有 Supabase 单次指令通道填写页面，同一浏览器等待人工操作，成功后先关闭 Chrome，再加密保存完整目录。遇站点本人验证，先完成验证，不能把登录页能打开算作登录成功。
11. 真实 Probe 通过后，用 **Make cards** 制作一个词，核对 Release ZIP/APKG/manifest 与音频。Telegram 仍按既有 Vercel 入口使用相同工作流；Anki 客户端导入由用户另机验收。

工作流均为手动入口；以后增加 `schedule` 时应沿用同一并发组和私有配置。当前没有自动定时发送豆包请求。

## 配置清单

| 名称 | GitHub 类型 | 用途 |
| --- | --- | --- |
| TS_OAUTH_CLIENT_ID | Secret | LearnWords 专用 OAuth client ID |
| TS_OAUTH_SECRET | Secret | 只可注册指定标签的临时节点 |
| BROWSER_PROFILE_KEY | Secret | 完整目录归档的 Fernet 密钥 |
| SUPABASE_URL | Secret | 已有私有会话项目 |
| SUPABASE_SERVICE_ROLE_KEY | Secret | 已有私有 bucket 的对象读写 |
| TS_EXIT_NODE | Variable | 服务器 Tailscale IPv4，当前 100.124.220.89 |
| TS_EXPECTED_IPV4 | Variable | 服务器实际公网 IPv4；宽带地址变化后重新核对并更新 |
| TS_EXPECTED_IPV6 | Variable，可空 | 服务器实际公网 IPv6；服务器没有公网 IPv6 时留空 |
| SESSION_MODE | Variable | 生产使用 profile |
| SUPABASE_SESSION_BUCKET | Variable，可选 | 默认 browser-sessions，必须为私有 bucket |
| SUPABASE_PROFILE_OBJECT | 工作流固定 | doubao-profile.tar.gz.fernet |
| CHROME_PATH | 自动发现 | Runner 镜像中的 Chrome 路径 |

Telegram、GitHub 发布凭据沿用 README 配置。生产 Secrets 不注入不可信 PR；Tests 不需要真实账号和 Tailscale 授权。

## 用户目录与加密

源配置为 `configs/dp.ini`；运行时独立保存在 `.session/doubao-browser/chrome.ini`。完整 User Data 根目录为 `.session/doubao-browser/profile/`，包含 `Local State`、`Default/` 和其他会话数据。ini 不能代替用户目录，不能只保存 `Default/`。

关闭 Chrome 后，Python 将 ini 与整个根目录 gzip 打包，排除普通缓存、锁、socket 与符号链接，再用 Fernet 认证加密上传。恢复时先验证并解密，再用 tarfile 的 data filter 解压；密钥错误或文件被篡改就停止，不降级到明文。新对象只存于已有私有 bucket，既不会提交 Git，也不会上传公开 artifact/Release。Fernet 会将压缩档案放进内存，适合当前几十 MB 的会话目录，不适合无限增长的文件库。

沿用所有浏览器工作流共用的并发组，避免同时覆盖对象。失败时执行退出路由、终止残留 Chrome 和删除私有工作目录；官方 Action 的 post 步骤负责退出 Tailscale。Chrome 未正常关闭时不归档其数据库，旧备份仍可恢复。未确认登录的目录不会覆盖正式归档。

Ubuntu 版本固定为 24.04，Chrome 由镜像提供，版本升级仍可能影响 profile。`--password-store=basic` 避免依赖跨 Runner 的桌面密钥服务，但运行目录在 Runner 上仍含敏感数据，必须依靠隔离环境、加密备份及清理。不能保证复制目录一定能恢复登录，应以新 Runner 的真实结果为准。

按用户要求使用 `--no-sandbox`；它会关闭 Chrome 浏览器沙箱，降低浏览器隔离强度，仅在受信任的一次性 Runner 运行。Xvfb 提供虚拟显示，Chrome 始终 `headless=False`。

## 常见故障

| 现象 | 检查与处理 |
| --- | --- |
| Tailscale 授权失败或标签无效 | 核对 OAuth 的 Auth Keys 写权限和精确标签；不要输出 secret 排查 |
| 找不到出口或未选中 | 确认服务器在线、广播和后台批准均完成，TS_EXIT_NODE 填 Tailscale IPv4 |
| 没有 tailscale0 | 使用 Linux 内核 TUN，检查工作流 tailscaled-args，不改成 userspace-networking |
| IP 与服务器不一致 / 地区不是 CN | 停止豆包访问；检查选中出口、上游 OpenClash、DNS 与宽带动态公网地址 |
| IPv6 不通 | 无公网 IPv6 的服务器可以只用已确认 IPv4；若配置了期望 IPv6 则必须检查通过。IPv6 能出网却没有对应服务器地址时也会停止 |
| DNS 返回 198.18.x.x | 通常是上游 fake-IP；检查服务器是否仍被 DNS 劫持，不能直接将假地址当真实网站 IP |
| 出口 CN 但豆包不能用 | 继续检查网页状态、区域限制提示、登录和单次真实查询；IP 地区不是可用性保证 |
| 解密失败 | 核对密钥及对象名，不重建密钥覆盖已有配置，不自动改读明文对象 |
| profile 下载 400/404 | 确认已执行显式 migrate，或已完成一次新 Login；不要把旧 gzip 对象直接改名为 .fernet |
| 登录未确认 | 保存私有诊断，核对实际页面；确实失效才重新登录，不连续发短信 |
| 返回发送失败 / 710022004 | 停止剩余单词和自动重试，检查账号验证与网站提示，不能用重复查询验收 |
| GitHub/Supabase 下载超时 | 第一阶段这些流量也可能经过大陆出口；先区分站点连通性和隧道问题，收尾仍恢复 Runner 路由 |

## 后续分流边界

当前是全局出口阶段，Python 依赖在启用出口前安装，浏览器任务期间的 GitHub/Supabase/Telegram 流量仍走当前出口。没有承诺只让豆包走中国大陆，也没有额外安装 mihomo、Clash 或 sing-box。

未来如需按目标分流，应单独设计豆包关联域名/IP、DNS 解析与 App Connector，并实测 IPv4/IPv6 和工作流控制流量。Tailscale Exit Node 本身不是任意域名规则引擎。

参考：[Tailscale Exit Nodes](https://tailscale.com/docs/features/exit-nodes)、[官方 GitHub Action](https://github.com/tailscale/github-action)、[Fernet](https://cryptography.io/en/latest/fernet/)。检索比较见 [设计记录](design.md)。
