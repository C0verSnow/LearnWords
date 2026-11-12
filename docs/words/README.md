# 词表来源与更新

实际选词入口一直是 `docs/words/vocabulary.txt`。issue #4 前这里只有 `approach`、`context`、`maintain`、`reliable`、`insight` 五个示例；现在由脚本生成指定雅思词表，一行一个词条。

来源是用户在 [issue #4](https://github.com/C0verSnow/LearnWords/issues/4) 指定的 [LynnShaw/vocabulary_for_ielts](https://github.com/LynnShaw/vocabulary_for_ielts)，固定读取 [4bf8da4 的 word_list.csv](https://github.com/LynnShaw/vocabulary_for_ielts/blob/4bf8da4c12fca6a9508f99dd71d7157495173882/word_list.csv)，避免上游更新悄悄改变词表。该文件的 Git blob SHA 为 `aadb479efff420a5bb7ee3936dee78bb11bf5742`。

该版本有 3632 条记录，只提取 `word` 列，统一小写和词间空白，按第一次出现的顺序去重，得到 **3592 个词条**。保留 9 个短语：carbon dioxide、el nino、bush fire、dining hall、ice cream、living room、new zealand、heart attack、health care。中文释义、原音标和章节信息不进入制卡数据；解释仍由豆包生成，英美音标和音频仍由 eSpeak NG 生成。

本次已在 GitHub 检索并核对来源：8 stars，最近提交为 2026-01-13，没有 issue 响应可供核实，仓库和 README 未声明许可证。它是用户明确指定的数据来源，不作为满足活跃开源筛选条件的实现参考，也不将其声称为 MIT 等授权。没有复制其页面或程序代码；CSV 读取使用 Python 标准库 `csv.DictReader`，不引入依赖。

## 重新生成

在仓库根目录执行以下数据生成命令（不是构建或测试）：

```sh
python -m scripts.import_vocabulary
```

离线或使用其他已准备好的同格式 CSV：

```sh
python -m scripts.import_vocabulary --source /path/to/word_list.csv
```

默认覆盖 `docs/words/vocabulary.txt`，可用 `--output` 指定其他文件。CSV 必须包含 `word` 列，词条允许英文字母、内部撇号、短横线和词间空格；缺列、空词条或无效字符会报错，解析成功后才写入文件。更改上游版本时修改导入脚本中的固定 URL，再重新生成并更新此说明与远端完整性断言，不手改生成的 TXT。

## 对制卡的影响

`next` 按此词表原顺序选词，`random` 从剩余词条中随机选择；都继续排除 `docs/records/generated.json` 中已交付的词。例如已发布的 approach 继续保留交付记录，在新词表中也不会再选到。耗尽时按原逻辑报告词表缺额，不清空历史解释、manifest 或 Release。

已有任务号继续使用其 manifest 保存的旧选词清单。要从新词表选词，请在合并 PR 后发起新的任务号。提交 PR 不会改变 main 上的生产词表。

## 验证

通过现有 GitHub Actions **Tests** 运行真实实现回归：CSV 带 BOM、带逗号的释义、重复词、短语、无效输入不覆盖词表；提交的 3592 个词条全部可选；已交付排除、耗尽、随机及顺序模式；真实 eSpeak NG 和 Anki 打包包含带空格词条的双口音媒体。测试无需访问上游 CSV 或豆包账号。按仓库约定不在本地编译或运行测试。

本次源代码提交 `1161ffc` 的远端 [Tests #43](https://github.com/C0verSnow/LearnWords/actions/runs/43132675432) 已通过，16 项测试全部成功；[PR #5](https://github.com/C0verSnow/LearnWords/pull/5) 保持打开等待用户 review，没有自动合并。
