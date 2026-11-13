import argparse
import json
import os
import re
import sys

from src.anki import build_package
from src.archive import build_archive
from src.config import ROOT, load_config, required_env
from src.content import parse_content
from src.doubao import Doubao, LoginExpired
from src.github import GitHub, GitHubError
from src.pronunciation import pronunciation
from src.repository import checkpoint, read_json, utc_now, write_json
from src.telegram import notify, send_document
from src.vocabulary import select_words


def run(args, config):
    output = ROOT / "output" / args.request_id
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "docs/manifests" / f"{args.request_id}.json"
    records_path = ROOT / "docs/records/generated.json"
    records = read_json(records_path, {})
    manifest = read_json(manifest_path, None)
    github = GitHub(required_env("GITHUB_TOKEN"), required_env("GITHUB_REPOSITORY"),
                    os.getenv("GITHUB_REF", "main"))
    if manifest and manifest["stage"] == "published":
        notify_delivery(args.chat_id, manifest, github, output)
        return 0
    if manifest is None:
        selected = select_words(ROOT / "docs/words/vocabulary.txt", records, args.count, args.mode)
        manifest = {"task_id": args.request_id, "requested": args.count, "mode": args.mode,
                    "selected": selected, "created_at": utc_now(), "stage": "selected"}
    try:
        release = github.find_release(args.request_id) if manifest.get("succeeded") else None
        if release and not release["draft"]:
            manifest["release_url"] = release["html_url"]
            record_delivery(manifest, records, records_path, manifest_path, github)
            notify_delivery(args.chat_id, manifest, github, output)
            return 0
        manifest.pop("error", None)
        manifest.update({"failed": {}, "succeeded": [], "shortfall": manifest["requested"] - len(manifest["selected"]),
                         "pronunciation_source": "eSpeak NG en-gb / en-us (synthetic IPA and WAV)"})
        write_json(manifest_path, manifest)
        cards = generate_cards(manifest, config, output, manifest_path)
        if not cards:
            manifest["stage"] = "failed" if manifest["selected"] else "no_available_words"
            write_json(manifest_path, manifest)
            checkpoint(ROOT, github.ref)
            notify(args.chat_id, summary(manifest))
            return 1 if manifest["selected"] else 0
        manifest["stage"] = "packaged"
        apkg = output / f"LearnWord-{args.request_id}.apkg"
        build_package(cards, apkg)
        write_json(manifest_path, manifest)
        asset_manifest = output / "manifest.json"
        write_json(asset_manifest, manifest)
        archive = output / f"LearnWord-{args.request_id}.zip"
        build_archive(apkg, manifest, archive)
        commit = checkpoint(ROOT, github.ref)
        manifest["release_url"] = github.publish(args.request_id, [apkg, archive, asset_manifest],
                                                 summary(manifest), commit)
        record_delivery(manifest, records, records_path, manifest_path, github)
        notify_delivery(args.chat_id, manifest, github, output, files=[apkg, archive])
        return 0
    except Exception as error:
        manifest["stage"] = "delivery_record_failed" if manifest.get("release_url") else "failed"
        manifest["error"] = type(error).__name__
        write_json(manifest_path, manifest)
        try:
            checkpoint(ROOT, github.ref)
        except Exception:
            print("检查点未能推送，请从 Actions artifact 取回中间结果。", flush=True)
        notify(args.chat_id, summary(manifest))
        print(f"任务失败：{type(error).__name__}；详情见任务清单。", flush=True)
        return 1
    finally:
        write_json(output / "manifest.json", manifest)


def notify_delivery(chat_id, manifest, github, output, files=None):
    notify(chat_id, summary(manifest))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not chat_id:
        return
    download = files is None
    if download:
        files = [output / f"LearnWord-{manifest['task_id']}.{suffix}" for suffix in ("apkg", "zip")]
    for path in files:
        try:
            if download:
                github.download_asset(manifest["task_id"], path)
            send_document(token, chat_id, path)
        except (GitHubError, RuntimeError, OSError):
            text = (f"{path.name} 发送失败或超过 Telegram 50 MB 上限；可从 Release 下载："
                    f"\n{manifest['release_url']}\n需要补发时，在 Actions 重跑原任务。")
            print(text, flush=True)
            notify(chat_id, text)


def record_delivery(manifest, records, records_path, manifest_path, github):
    manifest.pop("error", None)
    manifest["stage"] = "published"
    manifest["published_at"] = utc_now()
    for word in manifest["succeeded"]:
        records[word] = {"task_id": manifest["task_id"], "release_url": manifest["release_url"],
                         "generated_at": manifest["published_at"]}
    write_json(records_path, records)
    write_json(manifest_path, manifest)
    checkpoint(ROOT, github.ref)


def generate_cards(manifest, config, output, manifest_path):
    cards = []
    browser = None
    try:
        for index, word in enumerate(manifest["selected"]):
            content_path = ROOT / "docs/explanations" / f"{word}.json"
            for attempt in range(config["attempts"]):
                try:
                    cached = read_json(content_path, None)
                    if cached is None:
                        if browser is None:
                            browser = Doubao(config["doubao"])
                            browser.restore()
                        content = browser.generate(word)
                        write_json(content_path, content)
                    else:
                        content = parse_content(json.dumps(cached), word)
                    card = {**content, **pronunciation(word, output / "media")}
                    cards.append(card)
                    manifest["succeeded"].append(word)
                    manifest["stage"] = "content_generated"
                    break
                except LoginExpired as error:
                    for pending in manifest["selected"][index:]:
                        manifest["failed"][pending] = str(error)
                    return cards
                except Exception as error:
                    if attempt + 1 == config["attempts"]:
                        manifest["failed"][word] = type(error).__name__
            write_json(manifest_path, manifest)
            print(f"已处理 {index + 1}/{len(manifest['selected'])}：{word}", flush=True)
        return cards
    finally:
        if browser is not None:
            browser.close()


def summary(manifest):
    count = len(manifest["succeeded"])
    failed = len(manifest["failed"])
    stage = manifest["stage"]
    result = "部分成功" if failed or manifest["shortfall"] else "成功"
    state = result if stage == "published" else stage
    text = (f"LearnWord 任务 {manifest['task_id']}\n状态：{state}\n请求数量：{manifest['requested']}"
            f"\n已制卡：{count}\n失败：{failed}\n词表不足：{manifest['shortfall']}")
    if manifest.get("release_url"):
        text += f"\n{manifest['release_url']}"
    if manifest.get("error"):
        text += f"\n错误：{manifest['error']}，请在 Actions 重跑此任务。"
    if failed:
        text += "\n失败详情：" + "；".join(f"{word}: {error}" for word, error in manifest["failed"].items())
    return text


def parse_args(config):
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--mode", choices=("next", "random"), default="next")
    parser.add_argument("--request-id", default=f"run-{os.getenv('GITHUB_RUN_ID', 'manual')}")
    parser.add_argument("--chat-id", default=os.getenv("TELEGRAM_CHAT_ID", ""))
    args = parser.parse_args()
    if not 1 <= args.count <= config["max_cards"]:
        parser.error(f"count 必须在 1–{config['max_cards']}")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", args.request_id):
        parser.error("request-id 仅允许 1–80 个字母、数字、下划线或短横线")
    if args.chat_id and not re.fullmatch(r"-?[0-9]+", args.chat_id):
        parser.error("chat-id 必须是数字")
    return args


if __name__ == "__main__":
    configuration = load_config()
    sys.exit(run(parse_args(configuration), configuration))
