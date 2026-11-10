import json
import zipfile

IMPORT_GUIDE = """LearnWord 导入说明
在 Anki 选择 文件 > 导入，打开 LearnWord.apkg。
音频已包含在卡包中。请在客户端开启自动播放音频；正面包含英美两段发音。
音标和发音由 eSpeak NG 合成，不是真人词典录音；多音词需要人工核对。
同词使用固定模型和稳定 GUID，更新效果取决于客户端的导入选项。
本系统只制卡，不读取学习进度，也不安排复习。
"""


def build_archive(apkg, manifest, output):
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(apkg, "LearnWord.apkg")
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", IMPORT_GUIDE)
