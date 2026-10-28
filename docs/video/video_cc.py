#!/usr/bin/env python3
"""Generate the human-readable video script and the caption files from docs/video/script-v4.json.

Usage:
  python3 -I docs/video/video_cc.py docs/video/script-v4.json docs/video/out [--timings timings.json]

Outputs (in the out directory):
  VIDEO-SCRIPT-v4.md                 English production script (scene ids, visuals, mode captions, on-screen text,
                                     narration in the four languages)
  narration-<lang>.srt               narration captions (CC) per language
  onscreen-<lang>.srt                on-screen text per language, for the editor to place as titles
  narration-<lang>.txt               plain narration per language, one paragraph per scene, for the synthetic voice

--timings is an optional JSON {"S01": [start_seconds, end_seconds], ...} with the real timecodes of the final cut;
without it the planned start/end of each scene is used. Narration captions are split into blocks of at most
MAX_CHARS characters at sentence boundaries and spread evenly across the scene.

The em dash character is refused anywhere in the texts.
"""
import json
import re
import sys
from pathlib import Path

MAX_CHARS = 84
LANGS = ["en", "pt-BR", "es", "zh-CN"]


def fail(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(2)


def tc(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_sentences(text, lang):
    if lang == "zh-CN":
        parts = re.split(r"(?<=[。！？；])", text)
    else:
        parts = re.split(r"(?<=[.!?;:])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def blocks(text, lang):
    out, cur = [], ""
    for s in split_sentences(text, lang):
        if lang == "zh-CN":
            limit = 32
        else:
            limit = MAX_CHARS
        if cur and len(cur) + 1 + len(s) > limit:
            out.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip() if cur else s
        while len(cur) > limit:
            if lang == "zh-CN":
                # prefer a clause boundary (comma, colon, enumeration comma) before the limit
                cut = max(cur.rfind(ch, 0, limit) for ch in "，：、") + 1
            else:
                cut = cur.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            out.append(cur[:cut].strip())
            cur = cur[cut:].strip()
    if cur:
        out.append(cur)
    return out or [text]


def srt(entries):
    lines = []
    for i, (a, b, text) in enumerate(entries, 1):
        lines += [str(i), f"{tc(a)} --> {tc(b)}", text, ""]
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        fail("usage: video_cc.py script.json outdir [--timings timings.json]")
    script = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    timings = {}
    if "--timings" in sys.argv:
        timings = json.loads(Path(sys.argv[sys.argv.index("--timings") + 1]).read_text(encoding="utf-8"))

    raw = json.dumps(script, ensure_ascii=False)
    if "\u2014" in raw:
        fail("em dash present in script texts")

    scenes = script["scenes"]
    for sc in scenes:
        if sc["id"] in timings:
            sc["start"], sc["end"] = timings[sc["id"]]
        if not sc["end"] > sc["start"]:
            fail(f"{sc['id']}: end must be after start")
        for lang in LANGS:
            if lang not in sc["narration"] or lang not in sc["on_screen"]:
                fail(f"{sc['id']}: missing {lang}")

    # Markdown production script (English, with all narrations)
    md = [f"# Proof Before Pay: video production script v{script['version']}", ""]
    md.append(f"Base: {script['base_source']}. Target length {script['target_duration_seconds']} s. Master {script['master_language']}, "
              f"alternates {', '.join(script['alternate_languages'])}.")
    md.append("")
    md.append("## Rules")
    md.append("")
    for r in script["rules"]:
        md.append(f"- {r}")
    md.append("")
    md.append("## Scenes")
    for sc in scenes:
        md += ["", f"### {sc['id']}  {tc(sc['start'])[3:8]} to {tc(sc['end'])[3:8]}", "", f"Visual: {sc['visual']}", ""]
        if sc.get("mode_caption"):
            md.append(f"Mode caption (EN): {sc['mode_caption']['en']}")
            md.append("")
        md.append(f"On screen (EN): {sc['on_screen']['en']}")
        md.append("")
        for lang in LANGS:
            md.append(f"Narration {lang}: {sc['narration'][lang]}")
            md.append("")
    md += ["## Description block (EN)", "", script["description_block"]["en"], "", "## Scene checklist", ""]
    for c in script["scene_checklist"]:
        md.append(f"- {c}")
    md.append("")
    (out / "VIDEO-SCRIPT-v4.md").write_text("\n".join(md), encoding="utf-8")

    for lang in LANGS:
        nar, ons, plain = [], [], []
        for sc in scenes:
            bl = blocks(sc["narration"][lang], lang)
            span = (sc["end"] - sc["start"]) / len(bl)
            for i, b in enumerate(bl):
                a = sc["start"] + i * span
                nar.append((a, a + span - 0.05, b))
            caption = sc["on_screen"][lang]
            if sc.get("mode_caption"):
                caption = sc["mode_caption"][lang] + "\n" + caption
            ons.append((sc["start"], sc["end"] - 0.05, caption))
            plain.append(f"[{sc['id']}] {sc['narration'][lang]}")
        (out / f"narration-{lang}.srt").write_text(srt(nar), encoding="utf-8")
        (out / f"onscreen-{lang}.srt").write_text(srt(ons), encoding="utf-8")
        (out / f"narration-{lang}.txt").write_text("\n\n".join(plain) + "\n", encoding="utf-8")
        words = sum(len(sc["narration"][lang].split()) for sc in scenes)
        chars = sum(len(sc["narration"][lang]) for sc in scenes)
        print(f"{lang}: {len(nar)} narration blocks, {words} words, {chars} chars")
    print("ok", out)


if __name__ == "__main__":
    main()
