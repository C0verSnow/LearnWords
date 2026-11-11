# 现有 OpenWrt 路由器能不能直接做 Tailscale 大陆出口

评估时间：2026-11-11 11:07 UTC；Unix Timestamp：1794395242。本文件记录暂停实施阶段的评估快照；用户随后已选择继续使用 192.168.1.245，由主任务恢复服务器方案实施，路由器方案不实施。

## 结论

**硬件和系统具备运行条件，但这台路由器现在不能按官方软件包直接安装。主要卡点是永久存储，其次是现有 OpenClash 规则。当前更适合继续使用已准备好的大陆 Linux 服务器提供出口。** Runner、DrissionPage、Xvfb 仍留在 GitHub 托管 Runner，服务器或路由器只负责转发出口流量。

Tailscale 支持 Linux 出口节点；出口节点需要自己声明、管理员批准，以及客户端主动选择。提供出口本身不会让全家设备自动改走 Tailscale。[Tailscale 出口节点说明](https://tailscale.com/docs/features/exit-nodes)

## 本次已经确认的设备情况

以下来自本次现场只读检查，不是厂商性能承诺：

| 项目 | 当前情况 | 判断 |
| --- | --- | --- |
| 路由器 | Cudy TR3000 v1，ARMv8，aarch64_cortex-a53 | 官方有对应架构的软件包 |
| 系统 | OpenWrt 24.10.5，内核 6.6.119 | 不需要换系统才能研究这一方案 |
| 内存 | 总量 497424 KiB，最近可用 230552 KiB，约 225 MiB | 没有发现明显的内存门槛，但与 OpenClash 同跑的实际占用未测 |
| 永久存储 | /overlay 总量 44.6 MiB，最近只剩 7.2 MiB；较早读数为 8.1 MiB | 官方包空间不够 |
| 临时目录 | /tmp 早前约有 218.9 MiB，属于内存盘 | 不能当成重启后仍在的安装空间 |
| 隧道条件 | kmod-tun 已装，/dev/net/tun 存在，Tailscale 未装 | 已具备 TUN 基础条件 |
| 上网方式 | 无线客户端上联，WAN 是 10.20.x.x 私网地址 | 上游 NAT 不等于不能用，但直连质量未知 |

Tailscale 通常无需公网 IP 或手工端口转发，会尝试 NAT 穿透；直连失败时可经 DERP 中继。中继能提供连接，但不能保证与直连同样的速度。这里没有测到 Runner 到本地的实际直连、中继、吞吐或延迟。[Tailscale 官方联网说明](https://tailscale.com/docs/reference/faq/firewall-ports)

## 官方包到底要多少空间

已读取 **OpenWrt 24.10.5 / aarch64_cortex-a53** 的官方 Packages.gz，而非照抄其他架构或旧教程：

| 官方索引字段 | 实际值 |
| --- | --- |
| 版本 | 1.80.3-r1 |
| 包文件 | tailscale_1.80.3-r1_aarch64_cortex-a53.ipk |
| 下载大小 Size | 8929108 字节，约 8.52 MiB |
| 安装大小 Installed-Size | 23275520 字节，约 22.20 MiB |
| 依赖 | libc、ca-bundle、kmod-tun |
| 许可证 | BSD-3-Clause |

当前只剩 7.2 MiB，远低于官方声明的 22.20 MiB 安装大小，普通安装的空间检查无法满足。22.20 MiB 也不包含另外缺少的依赖、状态文件和日后升级余量；不应强行忽略空间检查。下载包可以放 /tmp，但安装展开后仍需要永久空间。以上是软件包元数据和容量对比，不是本次做过安装。[官方包索引](https://downloads.openwrt.org/releases/24.10.5/packages/aarch64_cortex-a53/packages/Packages.gz)

如果以后坚持路由器方案，优先另行确认可用的永久存储扩展，或用户明确愿意移除哪些现有组件后再评估；当前没有扩容、删包或更换固件。官方启动配置将节点状态存放在 /etc/tailscale/tailscaled.state；把程序临时放到 /tmp 运行也不能替代完整的重启恢复安排。[官方 OpenWrt 启动脚本](https://github.com/openwrt/packages/blob/openwrt-24.10/net/tailscale/files/tailscale.init)

## OpenClash 是第二个实际问题

现场看到 OpenClash 0.48.002，fake-ip 模式，开启 router_self_proxy。路由器本机 TCP 会被 output 规则转到 7892；入站 TCP 和 UDP 也会进入 OpenClash 的对应链，DNS 有劫持，fake-IP 198.18.0.0/16 流量可能进入 TPROXY，并设置 0x162 标记走表 354。

**据这些现有规则推断**，路由器直接做出口时，Runner 经 tailscale0 解密进入的上网流量，可能再次被 OpenClash 送去境外；Tailscale 本机的控制、DERP 等联网也可能被本机代理接管。这是规则层面的风险判断，尚未在路由器安装 Tailscale 验证。现有服务器按 MAC 绕过 OpenClash 的办法，不能直接套用到路由器自己的进程或 tailscale0 入站流量。

以后实施时需要只针对 Tailscale 的入站转发、本机联网和相关 DNS 做明确处理，让出口流量正常到 WAN，并具备必要的转发和 NAT；不需要把所有 LAN 流量送进 Tailscale。不能只凭“节点在线”就认定出口已经是大陆。Tailscale 的 netfilter 文档分别说明了接口接收、转发及 NAT 的责任。[Tailscale netfilter 说明](https://tailscale.com/docs/reference/netfilter-modes)

nftables 本身不是不支持：OpenWrt 24.10 的官方 Tailscale 启动脚本默认选择 nftables，Tailscale 官方也支持该模式。但“同用 nftables”不能证明它和当前 OpenClash 规则顺序已经兼容；也不宜直接关闭 Tailscale 的 netfilter 管理，否则必须自行承担完整的防火墙和 NAT 配置。[OpenWrt 官方配置](https://github.com/openwrt/packages/blob/openwrt-24.10/net/tailscale/files/tailscale.conf)、[Tailscale 防火墙模式](https://tailscale.com/docs/features/firewall-mode)

## GitHub 检索与候选比较

已检索 GitHub，找到官方项目和明确许可证的社区精简项目；没有下载执行安装脚本，也没有复制实现。

| 候选 | 实现和依赖 | 活跃度与已知限制 | 本次意见 |
| --- | --- | --- | --- |
| OpenWrt packages 官方包 | 上游 Tailscale 合并 CLI/daemon，裁剪部分功能；依赖 ca-bundle、kmod-tun | 仓库约 4670 stars，最近推送 2026-11-11；包声明 BSD-3-Clause。24.10 分支包为 1.80.3，当前空间不够 | 有永久空间后优先沿用官方包和服务流程 |
| Tailscale 上游精简设计 | 合并程序、裁剪少用功能，可再用 UPX 压缩；上游 BSD-3-Clause | 约 38919 stars，最近推送 2026-11-11；官方明确说明体积随版本、平台变化 | 可借鉴设计，不能用文档示例体积保证本机放得下；本次不编译 |
| GuNanOvO/openwrt-tailscale | OpenWrt SDK 加裁剪和 UPX，提供社区软件源；项目 MIT，保留 Tailscale BSD-3-Clause | 约 501 stars，最近推送 2026-11-03；Issue #169 有回复，报告 25.12/apk 升级后地址和 nft 规则丢失。该问题不是本机 24.10 的已证实故障 | 仅列调研候选；没有验证其具体 ARM64 包、安装展开大小和兼容性，不作为当前直接安装建议 |

活跃度数字为本次 GitHub API 查询快照，会继续变化；整体仓库活跃不代表每个旧分支都保持最新版本。[OpenWrt 包源码](https://github.com/openwrt/packages/blob/openwrt-24.10/net/tailscale/Makefile)、[Tailscale 上游](https://github.com/tailscale/tailscale)、[上游精简说明](https://tailscale.com/docs/how-to/set-up-small-tailscale)、[社区项目](https://github.com/GuNanOvO/openwrt-tailscale)、[社区 Issue #169](https://github.com/GuNanOvO/openwrt-tailscale/issues/169)

## 与现有大陆服务器比较

| 项目 | 已有 Linux 服务器 192.168.1.245 | 现有路由器 |
| --- | --- | --- |
| Tailscale 准备情况 | 1.104.5 已装，IP 转发已开，已声明出口，但尚未批准 | 尚未安装，先要解决永久空间 |
| 大陆出口情况 | 本次前序调整后，服务器直连 Cloudflare trace 显示 183.24.92.161、loc=CN；之前显示 JP | Tailscale 出口路径未建立、未验证 |
| OpenClash 处理 | 已按服务器 MAC 绕过；仍需日后验证完整 Runner 路径 | 还要处理 tailscale0 和路由器本机流量 |
| 本项目新增工作 | 主要剩出口批准及 Runner 整条链路验证 | 存储、安装、服务、防火墙及出口验证 |
| 作用 | 为 GitHub 托管 Runner 提供大陆网络出口 | 同样只提供出口，不承载浏览器 |

用户已选择保留已有服务器方案，并恢复该方案的后续实施。服务器自身 trace 显示 CN，只证明服务器当时的实际出口；**还不代表 GitHub Runner 已经借它成功出网**。本评估截止时，节点尚未批准、Runner 尚未连接；后续变化以主任务记录为准。路由器方案在解决永久空间及 OpenClash 分流后技术上可行，但没有实测性能依据，不能承诺更快或更稳。

本次只写评估文档；未安装软件、修改配置、运行测试或进行任何本地编译验证。OpenWrt Wiki 页面访问被站点保护拦截，因此关键结论使用可读取的官方包索引、官方源码和 Tailscale 官方文档交叉核对。
