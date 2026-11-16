# 245 恢复代理分流的记录

记录日期：2026-11-11（America/New_York）。修改前先完成只读评估，用户随后授权按需修改路由器。

## 现在怎么走

`192.168.1.245` 继续运行 Tailscale 出口节点，上网交给 `192.168.1.1` 的 OpenClash 分流。

| 请求 | 路由器的处理 | 实际检查 |
| --- | --- | --- |
| 245 访问豆包及仓库清单中的相关域名 | 优先直连 | 豆包 HTTP 200，连接记录为 DIRECT |
| 245 访问 www.cloudflare.com | 优先直连，供 LearnWords 检查出口 | 183.24.92.161，CN |
| 245 访问 Google | 沿用 google_domain 和 Google 策略组 | HTTP 204，连接记录显示代理节点 |
| 245 访问 YouTube | 沿用原有 YouTube 分流 | HTTP 200 |
| 245 访问 cloudflare.com，不带 www | 沿用普通境外分流 | 本次检查为 JP |
| GitHub Runner 的豆包请求 | Tailscale → 245 → 路由器直连 | 已有远端 network Probe 通过 |

最后两种 Cloudflare 域名故意分开验证，证明 245 既能直连也能使用境外代理。`www.cloudflare.com` 是现有出口检查的特定例外，不是按境外网站处理。

## 修改前查到了什么

- Tailscale 1.104.5 正常在线，节点地址为 `100.124.220.89`，广播 IPv4/IPv6 默认出口；没有健康告警。
- 245 的 `mihomo.service` 停止且未设开机启动，服务引用的 `/usr/local/bin/mihomo` 已不存在。日志最后停止时间为 2026-11-02 01:03:39（America/New_York），早于这次 LearnWords 的 Tailscale 调整；没有证据确定由哪个操作停用或移除。
- 路由器原本就是 rule 模式，国内策略组选中直连，境外策略组使用代理。245 的 MAC `08:e9:f6:79:37:4e` 在 OpenClash 整机绕过列表中。
- 修改前从 245 访问 Google 为 HTTP 000，访问 Cloudflare 为 CN，豆包根页面为 HTTP 302。
- 用户给出的 `myenv/config.yaml` 与路由器 `/etc/openclash/config/config.yaml` 经 YAML 解析后全部顶层配置相同，包括订阅、节点、策略组、分流规则、DNS 和 TUN，因此没有重复替换路由器源配置。

## 实际改了哪些地方

1. 从 `openclash.config.lan_ac_black_macs` 删除 245 的 MAC，让它重新参与分流和 DNS 处理。
2. 在 `/etc/openclash/custom/openclash_custom_rules.list` 前部加入 15 条规则：仓库 `configs/doubao-domains.txt` 的 14 个域名后缀，加上精确的 `www.cloudflare.com`。每条都同时要求来源为 `192.168.1.245/32`，目标为 `DIRECT`；开启 `enable_custom_clash_rules`。
3. 开启 OpenClash 自带的 `enable_meta_sniffer` 和 `enable_meta_sniffer_pure_ip`，让实际 IP 连接也能识别 TLS 域名；`override-destination` 仍为 false。这两个开关在路由器上全局生效，原有策略组和其余分流规则保留。
4. 在路由器已有 `/usr/share/openclash/openclash_reliability.rb` 持久覆写脚本中，为上述 15 个域名追加 fake-ip-filter，让它们返回真实地址，供 Runner 的 DNS 分流集合使用。这些域名的真实地址设置也适用于其他设备；优先直连规则仅适用于 245。
5. 用原有 `/etc/init.d/openclash restart` 流程生成并加载配置，没有手改生成的 `/etc/openclash/config.yaml`。
6. 清理一次 245 的 systemd-resolved DNS 缓存。切换后首次 Google 访问仍使用旧的错误解析地址 `157.240.7.20`，清缓存后由 OpenClash 正常提供解析并返回 HTTP 204，没有因此添加额外分流规则。

本次没有在 245 安装或启动第二套 Mihomo，没有替换它的 `/etc/mihomo/config.yaml`。当前由路由器已有 Mihomo 内核为 245 提供代理，避免同时维护两套自动路由。245 的 Tailscale 设置没有修改。

## 备份和恢复

修改前的路由器备份在 `/root/learnwords-split-backup-1794447016`，目录权限为 0700，含 UCI 配置、源 YAML、当时的运行 YAML、自定义规则、自定义覆写入口和 reliability 脚本。备份可能含订阅和控制凭据，不提交到仓库。

如需恢复本次修改前的整机绕过，在路由器执行：

```sh
cp -p /root/learnwords-split-backup-1794447016/openclash /etc/config/openclash
cp -p /root/learnwords-split-backup-1794447016/custom-rules.list /etc/openclash/custom/openclash_custom_rules.list
cp -p /root/learnwords-split-backup-1794447016/reliability.rb /usr/share/openclash/openclash_reliability.rb
/etc/init.d/openclash restart
```

这会恢复本次修改前的路由器设置；不要在以后已有其他新调整时直接覆盖。当前无需恢复。

## 验收范围

OpenClash 已完成一次正常重启，生成的运行配置有 46 条规则，新增 15 条在前，目标 fake-ip-filter 与域名嗅探均生效。实际连接记录确认豆包和指定 Cloudflare 检查命中来源 245 的 AND 直连规则，Google 命中 google_domain 并使用代理。

[远端 network Probe 43135116122](https://github.com/C0verSnow/LearnWords/actions/runs/43135116122) 使用现有 `feature/doubao-tailscale` 分支成功完成：Tailscale 连接、目标路径出口 CN、域名解析与入集、非目标服务保持 Runner 原出口、豆包 HTTP 200 且没有区域限制提示，以及退出清理。本次未打开登录会话、发送豆包对话或生成卡包。

只做了配置读取、Ruby 语法检查、真实远端网络检查和本地文档差异检查，未进行本地构建、编译或会触发编译的测试。没有安装新工具。

## GitHub 检索与采用的设计

本次在 GitHub 检索并查询 API：OpenClash 约 28,150 stars、MIT，Mihomo 约 35,691 stars、MIT，均有近期提交。数字为本次快照。OpenClash 沿用已有 Mihomo 内核，提供 UCI 访问控制、自定义规则和启动覆写；直接在 245 恢复 Mihomo 则要补回缺失的二进制，并额外处理它与 Tailscale 的 TUN 路由。本次按用户选择采用路由器已有流程，不引入新代理框架或复制第三方代码。

- [OpenClash 官方仓库](https://github.com/vernesong/OpenClash)：采用已有的访问控制与启动流程。
- [OpenClash 自定义规则入口](https://github.com/vernesong/OpenClash/blob/master/luci-app-openclash/root/etc/openclash/custom/openclash_custom_rules.list)：按来源和目标组合匹配，优先规则放前面。
- [Mihomo 官方规则说明](https://wiki.metacubex.one/config/rules/)：使用 AND、SRC-IP-CIDR、DOMAIN-SUFFIX 和 DOMAIN。
- [Mihomo DNS 配置](https://wiki.metacubex.one/config/dns/)：仅对需要真实地址的目标设置 fake-ip-filter。
- [Mihomo Linux 接口排除问题 #2605](https://github.com/MetaCubeX/mihomo/issues/2605)：维护者有回复并关联修复，报告者已确认修复。此问题涉及另一种 TUN 部署方式，不是本次路由器分流故障的原因。


## 2026-11-15：Issue #11 配置漂移修复

原任务 43792473303 和 feature 分支复现 43794590784 都在出口检查失败。只读检查发现：路由器当前运行配置中，此前的 15 条 LearnWords 域名直连规则和真实 DNS 例外已不在；旧 reliability.rb 仍保存 DNS 例外，但当前自定义覆写入口没有调用该脚本。不能仅凭文件时间判断是谁移除了配置。

245 的 Tailscale 在线。先在 245 上用普通解析访问 www.cloudflare.com，再用 `curl --resolve www.cloudflare.com:443:104.16.123.96` 排除假 DNS，两次实际出口都是 US。这说明本机安装 Mihomo 并把域名设为 DIRECT，仍会经过当前默认网关 192.168.1.1，被路由器再次处理；除非另有独立大陆出站通道，否则单独添加一层本机代理不能解决已观察到的问题。本次只核对旧 Mihomo 服务、配置与网卡，没有安装、启动或修改 245 上的 Mihomo。

用户先要求修改前告知，再提出优先考虑 245 本机分流，明确同意该方案不适用时修改路由器。执行前已说明将修改 1.1 的两份持久配置并重启 OpenClash；245 不改配置。

本次只修改：

1. `/etc/openclash/custom/openclash_custom_rules.list`：在前部恢复仓库 `configs/doubao-domains.txt` 中 14 个域名后缀和精确 www.cloudflare.com 的 15 条来源 192.168.1.245/32 的 DIRECT 规则。保留当时已有的两条 Tailscale UDP 规则。
2. `/etc/openclash/custom/openclash_custom_overwrite.sh`：使用官方 `ruby_arr_insert_arr` 和 `ruby_uniq`，把上述域名追加到 `dns.fake-ip-filter`。不重新启用旧 reliability.rb 中无关的健康检查修改，保留已有的源 sniffer 覆写。

没有手改生成的 `/etc/openclash/config.yaml`，也没有修改订阅、代理组、整机绕过、245 网络或 Tailscale 设置。真实 DNS 例外会影响其他设备对这些域名的解析，DIRECT 规则仅匹配来源 245。

修改前两份源文件、UCI 配置与运行配置保存在路由器私有目录 `/root/learnwords-issue11-backup-1794798014`，目录为 0700。先核对源文件与评审差异没有变化，再校验暂存的 shell 语法及规则 YAML，回读内容一致后替换源文件，执行原有 OpenClash restart。重载后比较 YAML，顶层只有 dns、rules 两项变化，sniffer 与其他配置相同；17 条 245 规则包含恢复的 15 条和原有 2 条 UDP 规则。

重启后豆包 DNS 返回真实公网地址，245 使用同一个真实 IP 的 HTTPS 出口恢复为 `183.24.92.161 / CN`。远端 [Tests 43795260065](https://github.com/C0verSnow/LearnWords/actions/runs/43795260065) 通过；完整制卡结果另在后续验收记录中核对。

如需撤回本次路由器修改，先确认之后没有其他人改动同名文件，再恢复这两份源文件并重载：

```sh
cp -p /root/learnwords-issue11-backup-1794798014/openclash_custom_rules.list /etc/openclash/custom/openclash_custom_rules.list
cp -p /root/learnwords-issue11-backup-1794798014/openclash_custom_overwrite.sh /etc/openclash/custom/openclash_custom_overwrite.sh
/etc/init.d/openclash restart
```

不要恢复旧运行 config.yaml 替代正式重载，也不要为了通过制卡检查删除 IP/CN 校验。


完整验收：[Make cards 43795583719](https://github.com/C0verSnow/LearnWords/actions/runs/43795583719) 从新的 Runner 恢复原登录，在线生成 catastrophic、calamity、endanger、jeopardise、destructive，5/5 成功，清单为 published，failed 为空且 shortfall 为 0。原登录无需重做，加密档案正常保存，路由清理与官方 Action 退出均成功。既有私聊配置非空，通知及 APKG 交付未出现失败提示。

[Release](https://github.com/C0verSnow/LearnWords/releases/tag/learnword-verify-issue11-make5) 的 APKG 为 490,930 字节，SHA-256 为 `b176fdec1e1d25f6710f828fe3def6eace5aede0f5034f49b6db775f5bf724c6`，与发布 digest 一致；静态读取确认 5 条笔记、5 张卡片、10 段 22050 Hz 的有效 WAV，ZIP 内外 APKG 完全相同。Anki 客户端导入和实际收听仍由用户另机验收，本机没有编译、构建或运行测试。
