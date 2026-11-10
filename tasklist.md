# 本文档为4象限的任务清单，全文书写大白话

## 想做：
- [1794301047] 完成 issue #1：通过 Telegram 发起任务，在 GitHub Actions 操作豆包，制作并发布带音频的 Anki 卡包。

## 做完：
- [1794302078] 修正后的远端 Tests 再次通过：12 个测试全部通过，含真实 Chrome 测试页、APKG 音频、HTTP Webhook、发布重跑及缺失交付记录恢复：https://github.com/C0verSnow/LearnWords/actions/runs/42788782351 。
- [1794302078] 已更新 PR #2 的实现说明、测试证据和未做的真实账号验收项；按 issue 原文要求关闭 issue #1，PR 保持打开等用户 review，没有合并。
- [1794301951] 已建 PR #2 等用户 review，没有合并。首轮远端 Tests 通过，12 个测试通过：https://github.com/C0verSnow/LearnWords/actions/runs/42788383796 。
- [1794301951] 修正重跑后残留旧错误和公开 Release 后记录缺失的恢复行为，补充测试；准备运行最终远端 CI。
- [1794301783] 完成 Webhook、持久化请求去重、选词、豆包接口、会话实验工具、双口音 TTS、APKG/ZIP、Release 和检查点恢复代码。
- [1794301783] 检索并比较 DrissionPage、Playwright、genanki、eSpeak NG，记录维护情况、许可和设计取舍到 docs/design.md。
- [1794301783] 用户确认尚无账号配置，先交付代码和配置说明；真实豆包恢复和部署联调没有做，文档不声称已经验证。
- [1794301047] 同步了只有 README 的远端仓库，读完 issue 和补充讨论，建立 feature 分支。

## 没做：
- [1794302078] 用户尚无账号配置，本次未部署 Vercel/Telegram/Supabase，未验证豆包线上选择器、跨 Runner 登录恢复或 Anki 客户端导入；README 和 docs/session-research.md 已列出配置与验收步骤。
- [1794301047] 按约定不做本地构建、编译或会触发编译的验证；远端测试和真实登录实验另行记录。

## 在做：
- [1794302078] 等待用户 review PR #2，本次代码和配置说明已经交付，没有自动合并。
