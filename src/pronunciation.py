import subprocess
import wave


def pronunciation(word, directory):
    directory.mkdir(parents=True, exist_ok=True)
    data = {}
    for accent, voice in (("UK", "en-gb"), ("US", "en-us")):
        result = subprocess.run(["espeak-ng", "-q", "--ipa", "-v", voice, word],
                                check=True, capture_output=True, text=True, timeout=20)
        ipa = result.stdout.strip()
        if not ipa:
            raise ValueError(f"{accent} 音标为空")
        path = directory / f"learnword_{word}_{accent.lower()}.wav"
        subprocess.run(["espeak-ng", "-v", voice, "-w", str(path), word],
                       check=True, capture_output=True, timeout=20)
        with wave.open(str(path)) as audio:
            if audio.getnframes() == 0:
                raise ValueError(f"{accent} 发音文件为空")
        data[f"IPA_{accent}"] = ipa
        data[f"Audio_{accent}"] = str(path)
    return data
