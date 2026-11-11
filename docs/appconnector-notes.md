# 豆包域名经大陆服务器的 App Connector 研究

记录时间（Unix Timestamp）：1794398370。只查官方文档和 Tailscale 官方 GitHub 的 v1.104.5 源码；未改服务器、Tailnet 策略或工作流，未做本地编译与测试。

## 可以确定的事

- App Connector 会把域名解析出的地址公布成 IP 路由。它不是按每个 HTTPS 请求的域名选出口：两个域名共用一个 IP 时，都可能经大陆服务器。因此可以实现“豆包所需地址走大陆、其他地址走 Runner”，不能保证“其他所有域名绝对保持原出口”。应只加入实际需要的域名，避免整片 CDN 通配符。[官方机制及共用 IP 限制](https://tailscale.com/docs/features/app-connectors#considerations)
- 当前官方文档明确给出 `nodeAttrs.target: ["tag:example-connector"]`，通用 target 支持 tag、用户、group、`*`；它表示哪台设备收到能力配置。v1.104.5 读取自己 `CapMap` 中的配置，无需把能力发给 CI 才能转发。它不是“哪些客户端允许使用”的名单。[官方能力解释](https://tailscale.com/docs/reference/node-attributes-vs-app-capabilities#application-capabilities-in-both-sections)、[v1.104.5 实现](https://github.com/tailscale/tailscale/blob/v1.104.5/ipn/ipnlocal/local.go#L5975)
- setup 和 best-practices 示例仍写 `target: ["*"]`。当前文档虽支持窄 target，但公开资料没有说明控制平面如何据此生成其他客户端的隐式 split DNS；不能声称 `target: ["tag:learnwords-ci", "tag:connector"]` 就让其他用户完全不受 DNS/路由影响。控制平面配置不是仅由 Linux 1.104.5 版本决定，必须在实际 Tailnet 对比 CI 与现有客户端下发配置。[setup](https://tailscale.com/docs/features/app-connectors/how-to/setup)、[split DNS 工作方式](https://tailscale.com/docs/reference/best-practices/app-connectors#dns-lookups)
- v1.104.5 `connectors` 只认 `"*"` 或标签；把 `100.124.220.89`、`192.168.1.245` 或用户邮箱填进去不会选中当前服务器。源码只检查通配符或服务器的 Tags。[配置类型](https://github.com/tailscale/tailscale/blob/v1.104.5/types/appctype/appconnector.go#L70)、[匹配实现](https://github.com/tailscale/tailscale/blob/v1.104.5/ipn/ipnlocal/local.go#L6022)
- 保留服务器当前用户身份时，可以用 `connectors: ["*"]`，前提是确认没有其他设备广播 App Connector；否则它们也会被选中。`autoApprovers.routes` 支持当前用户的完整登录名、group、tag，官方没有列出设备 IP。用当前用户作自动批准者会覆盖该用户其他设备的路由广播；也可先不加自动批准，逐条手动批准学习路由。专用 tag 是官方常规方案，但会改变当前设备身份，不能顺手套用。[autoApprovers 语法](https://tailscale.com/docs/reference/syntax/policy-file#auto-approvers)

## 最小权限与网络条件

CI 继续保留现有 `autogroup:internet` grant，只需新增下面的 PeerAPI 可见性权限；不需要把服务器 SSH、LAN 或所有端口开放给 CI。它不是另装一个 53 端口 DNS 服务：真实 DNS discovery 用 PeerAPI DoH。[官方 DNS 最小授权](https://tailscale.com/docs/reference/best-practices/app-connectors#port-access-for-dns-discovery)

```json
{"src": ["tag:learnwords-ci"], "dst": ["100.124.220.89"], "ip": ["tcp:53", "udp:53"]}
```

IP 可用于 grant 目的地址，不能因此推论它也可用于 `connectors` 或 `autoApprovers`。现有用户与 TGBot 原先的全网授权保留后，它们也可能有足够权限看到 connector；只给 CI 新加 DNS grant 不能撤销已有授权。[策略地址选择器](https://tailscale.com/docs/reference/syntax/policy-file#dst)

官方 setup 写了“公开可访问 IP”要求，但官方连接文档也明确讨论了 NAT 后面的 app connector、DERP 回退与 NAT 出口。独立公网 IP 不是可据此断言的协议硬门槛；当前已证实直连与 CN 出口是可行依据，仍须真实验证 App Connector 的 DNS 和目标访问。NAT 主要影响隧道直连与性能；公网出口会是现有上游 NAT 地址。[官方连接类型](https://tailscale.com/docs/reference/connection-types#exit-nodes-and-terraform)、[官方 NAT 排障](https://tailscale.com/docs/reference/troubleshooting/network-configuration/hard-nat-issues)

App Connector 同时学习 A 和 AAAA，源码按地址长度生成 /32 或 /128。IPv4 出口正常不代表 IPv6 正常；当前服务器无公网 IPv6 时，不应直接批准 IPv6 路由并宣称可用，也不能只漏掉 IPv6 自动批准后任由浏览器从 Runner 直出。需要让这次 Runner 的豆包访问确定使用 IPv4，或补足服务器真实 IPv6 后再验收。[官方 A/AAAA 说明](https://tailscale.com/docs/reference/best-practices/app-connectors#domains)、[v1.104.5 路由实现](https://github.com/tailscale/tailscale/blob/v1.104.5/appc/appconnector.go#L379)

## 本次决定

本次不启用 App Connector。当前证据不能保证只改变 CI 的 DNS/路由；为了配合它改服务器 tag 身份、放宽用户级自动批准或新增 Tailnet 权限，也不符合这次保持现状的边界。

改在短命 GitHub Runner 内处理域名发现与分流，沿用已有 Tailscale Exit Node 通道，服务器和 Tailnet 权限不变。这个选择只把配置作用域收在 Runner 内，并不能消除 IP 共用的限制：任何按解析后 IP 分流的方案，仍会把同一 IP 的其他域名流量顺带送往大陆。实现与验收都要如实保留这项边界。

IPv6 同样需要明确处理：服务器没有公网 IPv6 时，豆包域名的 AAAA 不能从 Runner 原生 IPv6 绕过大陆，也不能送入不能出网的 IPv6 路径后宣称可用。应在本次 Runner 内保证目标访问使用可达的大陆 IPv4，同时不改其他设备的 IPv6 设置。上述为本研究给出的边界，实际 Runner 实现另行记录。

借鉴项目：[tailscale/tailscale](https://github.com/tailscale/tailscale)，BSD-3-Clause；本次已在 GitHub 检索到所需 App Connector 官方实现，按 v1.104.5 阅读而未复制业务代码。当前只有研究结论，以上配置尚未实施。
