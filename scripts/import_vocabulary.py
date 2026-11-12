import argparse
import csv
import io
from pathlib import Path
from urllib.request import urlopen

from src.vocabulary import WORD

SOURCE_URL = (
    "https://raw.githubusercontent.com/LynnShaw/vocabulary_for_ielts/"
    "4bf8da4c12fca6a9508f99dd71d7157495173882/word_list.csv"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "docs/words/vocabulary.txt"


def import_vocabulary(source, output):
    words = read_words(source)
    output.write_text("\n".join(words) + "\n", encoding="utf-8")
    return len(words)


def read_words(source):
    reader = csv.DictReader(io.StringIO(source.lstrip("\ufeff")))
    if not reader.fieldnames or "word" not in reader.fieldnames:
        raise ValueError("CSV 缺少 word 列")
    words = {}
    for line, row in enumerate(reader, start=2):
        word = " ".join((row["word"] or "").lower().split())
        if not WORD.fullmatch(word):
            raise ValueError(f"CSV 第 {line} 行不是有效的英文单词或短语：{word!r}")
        words.setdefault(word, None)
    if not words:
        raise ValueError("CSV 没有词条")
    return list(words)


def main():
    parser = argparse.ArgumentParser(description="从指定雅思 CSV 生成一行一个词条的词表")
    parser.add_argument("--source", type=Path, help="本地 CSV；默认下载固定版本的雅思词表")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.source:
        source = args.source.read_text(encoding="utf-8-sig")
    else:
        with urlopen(SOURCE_URL, timeout=30) as response:
            source = response.read().decode("utf-8-sig")
    count = import_vocabulary(source, args.output)
    print(f"已写入 {count} 个去重词条：{args.output}")


if __name__ == "__main__":
    main()
