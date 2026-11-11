import json
import re

FIELDS = ("Intuition", "Meaning", "Usage", "Examples", "Comparison", "MemoryTip")


def prompt(word):
    return (
        f"请为英语单词 {word} 制作学习内容。只返回一个 JSON 对象，不要 Markdown。"
        f"Word 必须为 {word}，其他键为 {', '.join(FIELDS)}，所有值为非空字符串。"
        "Intuition：用大白话解释母语者的直觉；Meaning：核心含义；Usage：常见场景；"
        "Examples：至少两条例句，每条含英文和中文翻译；Comparison：易混词对比；"
        "MemoryTip：一句简短提示。使用中文讲解，不编造词源，不返回音标或音频。"
    )


def parse_content(text, word):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("DeepSeek回答不是完整 JSON") from None
    if not isinstance(data, dict) or data.get("Word") != word:
        raise ValueError("DeepSeek回答的单词不匹配")
    if any(not isinstance(data.get(key), str) or not data[key].strip() for key in FIELDS):
        raise ValueError("DeepSeek回答缺少完整的解释字段")
    return {key: data[key].strip() for key in ("Word", *FIELDS)}
