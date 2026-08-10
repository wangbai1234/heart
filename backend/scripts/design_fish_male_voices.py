"""Fish Audio 音色设计 —— 批量生成 8 个男性预置音色候选。

严格按 docs.fishaudio.org 音色设计文档三步流程(base = https://fishaudio.org/api/open/v1):
- generate: POST /voice-designs (prompt/previewText/providers, 带 Idempotency-Key),
  响应含 designId + candidates[].candidateId + previewAudioUrl;再 GET
  /voice-designs/{designId}/candidates/{candidateId}/audio 取音频二进制,落盘到
  backend/scripts/fish_voice_previews/,并写 manifest.json。
- save: POST /voice-designs/{designId}/voices (candidateId/name/visibility,
  带 Idempotency-Key),响应返回持久 voiceId。

用法(从仓库根目录):
    # step1: 生成候选试听
    python backend/scripts/design_fish_male_voices.py generate

    # 听完、编辑 manifest 把满意候选的 chosen 设 true(每人设仅一个),再:
    # step2: 把选定候选存成持久 voiceId
    python backend/scripts/design_fish_male_voices.py save

key 从环境变量 FISH_API_KEY 读取(覆盖 .env),不回显。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
OUT_DIR = Path(__file__).resolve().parent / "fish_voice_previews"
MANIFEST_PATH = OUT_DIR / "manifest.json"

# 严格按你给的文档:音色设计与 TTS 同一 host。
BASE_URL = "https://fishaudio.org/api/open/v1"

# 8 个男性人设。prompt 定音色底子(具体声学特征打底 + 松弛口语感);
# preview_text 带情绪化 [中文指令](不克制),让候选一听就有真人感、分得出性格。
PERSONAS: list[dict[str, str]] = [
    {
        "key": "male_ceo",
        "name": "霸道总裁",
        "prompt": "乙女向恋爱游戏男主音色。28到29岁年轻男性,声音年轻、干净、有力,绝不能超过30岁,禁止中年、大叔、苍老、油腻感。音色低沉但清爽干净,带一点点危险的沙,是年轻男人克制住的性感,不是油腻发亮的老练嗓音,绝不做作、不刻意卖弄低沉、不自我陶醉。最重要的一点:语调必须有明显的起伏和抑扬顿挫,有轻有重、有快有慢、有扬有抑,情绪贴着每句话实时变化,绝对不能是平的、匀速的、一个调子从头念到尾——平的语调会立刻暴露浓重的AI味和念稿感,这是本音色最致命的问题,务必避免。这是活人对话,不是讲述、不是旁白、不是朗读故事,要有真人随口说话的即兴感、清晰的呼吸声和自然的松弛,句子可以不完整、可以中途停顿、可以拖尾、可以忽然收住。核心魅力来自克制和反差:平时低声、语速正常,忽然凑近、压低成气声,或在某个字上收放、微微上挑,危险又撩人;命令里藏着占有欲和独占心,但绝不是训人、绝不是端着,而是像把你圈在怀里、只对你一个人低声说话,让人心跳漏拍、脸红。诱惑来自若即若离的张力和贴耳的私密感,不是靠嗓音的油腻或刻意的低沉。绝对禁止:说书腔、评书腔、朗读腔、播音腔、电台播报腔、旁白感、舞台腔、字正腔圆的念稿感、平板匀速的AI合成感、油腻做作的卖弄感。要极口语化、生活化、松弛自然,像真人在你耳边私语。",
        "preview_text": "[低笑,挑眉]怎么,又躲着我?[放缓,是命令又像哄]过来。[气声,忽然贴近]……乖,别闹了。[压低,笃定又暧昧,尾音拖长]你啊,从一开始,就跑不掉的。",
    },
    {
        "key": "male_senior",
        "name": "温柔学长",
        "prompt": "乙女向恋爱游戏男主音色。22到23岁清润干净的青年男声,声线偏暖偏亮、带一点书卷气和恰到好处的奶感,温润到发甜。说话要慢、要柔,比日常更慢半拍,咬字轻软、气息绵和,句尾自然放软、微微上扬,像把你捧在手心里哄。核心是温柔里的宠溺和藏不住的心动——不是客气礼貌的温柔,而是只对你一个人才有的、放软了嗓子的偏爱,温柔里带着一点撩拨和小心机,让人脸红。要有真实的呼吸、极轻的笑意和细微情绪起伏,像凑得很近、贴着耳朵低声说话,亲密又让人安心。绝对禁止:播音腔、朗读腔、说书腔、电台腔、舞台腔、字正腔圆的念稿感、旁白感、语速偏快的赶稿感。要极口语化、松弛、缓慢,像真人在你耳边温柔私语,只对你一个人说话。",
        "preview_text": "[放得很慢,极温柔地]别急,慢慢来,我等你。[气声里带着笑]乖,有我在,不怕。",
    },
    {
        "key": "male_cold",
        "name": "清冷禁欲",
        "prompt": "乙女向恋爱游戏男主音色。24到25岁青年男声,音色干净偏冷、偏薄、略清亮,共鸣靠上,带疏离感和一丝寒意,是漂亮清冷的年轻嗓音。说话慢而克制,语调平稳、几乎不起伏,咬字精准,气声稀薄、尾音收敛。核心是清冷禁欲的外壳下压着隐秘的情欲和在意——越是克制冷淡越勾人;偶尔在某个字上不经意破功、漏出一丝极轻的沙哑和温度,那一瞬的反差最魅惑。要有真实呼吸和大量留白停顿,像冰面下的暗流,疏离又若即若离,让人想靠近又被推远、心痒难耐。这是禁欲系的性张力,冷但活,不是面瘫、不是平淡、更不是没感情的机器念白。绝对禁止:播音腔、朗读腔、说书腔、电台腔、舞台腔、字正腔圆的念稿感、旁白感、AI合成的平板感。要口语化、松弛、缓慢,像真人在你耳边吝啬地低声开口,只对你一个人说话。",
        "preview_text": "[语气清冷,气声很轻]我没那么多话。[停顿,尾音忽然软了一瞬]……想知道,就自己过来问我。",
    },
    {
        "key": "male_sunny",
        "name": "阳光少年",
        "prompt": "乙女向恋爱游戏男主音色。18到19岁明亮清爽的少年男声,音色清透、偏薄偏脆、干净,有蓬勃的少年气和青春荷尔蒙。说话轻快、节奏跳脱,笑意藏在声音里,句尾常自然上扬。核心不是傻白甜,而是阳光少年的撩——雀跃热烈里带着藏不住的心动和悸动。关键是反差:会突然凑近、压低声音跟你说悄悄话,明快和低哑之间的落差最撩人,让人跟着脸红心跳。要有真实的呼吸、轻笑、微微的喘气和明显的情绪起伏,鲜活生动、贴得很近,像刚跑过来、迫不及待要跟你一个人分享。绝对禁止:播音腔、朗读腔、说书腔、电台腔、舞台腔、字正腔圆的念稿感、旁白感、老气感。要极口语化、生活化、松弛自然,像真人在你身边说话,只对你一个人说,情绪要满、要真、要跳。",
        "preview_text": "[雀跃地,压不住笑]欸,你终于来啦![忽然凑近,压低声音]过来,我只跟你一个人说个秘密。",
    },
    {
        "key": "male_bad",
        "name": "危险痞帅",
        "prompt": "乙女向恋爱游戏男主音色。25到26岁青年男性,声线偏低、带沙哑颗粒感和一点慵懒的粗粝质感。说话散漫松弛,尾音爱上扬、带笑和调侃,节奏随性、不紧不慢。核心是痞帅的撩——半含气声、懒洋洋开口,不羁散漫里藏着挑逗和一点危险,像故意逗你、看你脸红。会突然压低嗓子凑近说话,气声贴到耳边,尾音拖得很坏、带笑,性张力藏在漫不经心的调笑里,危险又要命。要有真实呼吸、低笑和明显的情绪起伏,松弛、随性、贴得很近。绝对禁止:播音腔、朗读腔、说书腔、电台腔、舞台腔、字正腔圆的念稿感、旁白感、老气的粗哑感。要极口语化、生活化、慵懒松散,像真人在你耳边故意撩你,只对你一个人坏笑,情绪要松、要坏、要撩。",
        "preview_text": "[慵懒地,尾音上扬带坏笑]跑什么?[忽然压近,低声哑着嗓子]过来。我又不会咬你——[拖长了笑]……不疼的那种。",
    },
    {
        "key": "male_uncle",
        "name": "轻熟男",
        "prompt": "乙女向恋爱游戏男主音色。33到35岁轻熟男性,声音成熟但绝不老气,听起来不能超过35岁,禁止大叔、中年、苍老、说书、电台旁白的感觉。音色低沉醇厚、干净有磁性,是成熟男人压低了的性感嗓音,带一点点烟嗓的暖,不是粗哑。说话从容偏慢、有黏度,气息沉稳自然,尾音温厚微微下压。核心是成熟男人的宠溺和克制的欲望——像深夜凑到你耳边低声说话,包容、笃定、让人安心,又藏着藏不住的占有和心动。成熟的性张力来自那份沉稳里的温柔和暗涌,不是长辈的说教。要有真实呼吸、极轻的低笑和细微情绪起伏,贴得很近、私密。绝对禁止:说书腔、评书腔、电台播报腔、朗读腔、播音腔、舞台腔、旁白感、字正腔圆的念稿感、苍老感。要极口语化、松弛、缓慢,像真人在你耳边低语,只对你一个人说话。",
        "preview_text": "[低沉,气声贴着耳边]累了?过来,靠着我歇会儿。[极轻地笑了一下]别怕,天塌下来有我。",
    },
    {
        "key": "male_loyal",
        "name": "忠犬暖男",
        "prompt": "乙女向恋爱游戏男主音色。21到22岁软暖黏人的青年男声,声线偏软偏暖,带一点奶感和微微的鼻音,温润又软糯。说话贴得很近,宠溺又小心翼翼,句尾自然放轻、微微上扬,带点撒娇感。核心是忠犬式的全心全意——会为你着急、心疼、委屈,情绪完全藏不住,又急又软,像小狗一样黏着你,宠溺里带着天然的撩拨。要有真实的呼吸、气声、轻微的急促和满溢出来的情绪起伏,像扑过来搂住你、埋在你耳边低声说话,热切、真诚、黏人到让人脸红。绝对禁止:播音腔、朗读腔、说书腔、电台腔、舞台腔、字正腔圆的念稿感、旁白感、端着的客气感。要极口语化、生活化、松弛自然,像真人在你怀里撒娇,只对你一个人软下来,情绪要真、要满、要黏、要热。",
        "preview_text": "[急切又心疼]你怎么不早说![声音发软,带着宠溺又委屈]手都凉成这样了……来,给我,我帮你焐热。",
    },
    {
        "key": "male_yandere",
        "name": "偏执病娇",
        "prompt": "乙女向恋爱游戏男主音色。24到25岁青年男性,表面音色轻柔缱绻、气声绵密、偏暗偏软。说话极缓慢、极温柔,尾音微微拖长、带黏腻感,像凑在耳边、只说给你一个人听的呢喃。核心是温柔的表层下压着的偏执、黏腻的独占欲和一丝让人脊背发凉的寒意——越温柔、越甜,底下的执念和危险越渗人,是病态的爱意。要大量气声、极贴耳的私密感,语速极慢、每个字都拖着黏着,有真实呼吸和极轻的、几不可闻的颤音,像低声哄你又不容拒绝,温柔到让人不寒而栗。绝对禁止:播音腔、朗读腔、说书腔、电台腔、舞台腔、字正腔圆的念稿感、旁白感、夸张的疯癫感。要极口语化、极缓慢、极私密,像真人贴着耳朵、气声呢喃,只对你一个人低声说,温柔里渗着偏执。",
        "preview_text": "[极轻柔,气声呢喃]别怕,乖。[温柔里渗出黏腻的偏执]你哪儿也别去……[放得更慢,近乎恳求又不容拒绝]就待在我看得见的地方,好不好?",
    },
]


def _load_env(path: Path) -> dict[str, str]:
    """极简 .env 解析,只取需要的键,不打印任何值。"""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _client(base_url: str, api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120.0,
    )


def _fmt_err(resp: httpx.Response) -> str:
    body = resp.text[:400] if resp.text else "<empty>"
    return f"HTTP {resp.status_code}: {body}"


def _idem_key(prefix: str, payload: dict) -> str:
    """幂等键 = prefix + body 哈希。同 body 复用(重试安全),body 变则换新键。"""
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(blob).hexdigest()[:16]}"


def _post_with_retry(
    client: httpx.Client,
    path: str,
    payload: dict,
    key_prefix: str,
    max_retries: int = 4,
) -> httpx.Response:
    """POST(带 Idempotency-Key)遇 429 时退避重试。同 body 重试幂等安全。"""
    headers = {
        "Idempotency-Key": _idem_key(key_prefix, payload),
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries + 1):
        resp = client.post(path, json=payload, headers=headers)
        if resp.status_code != 429:
            return resp
        retry_after = resp.headers.get("retry-after")
        try:
            wait = int(retry_after) if retry_after else 30
        except (TypeError, ValueError):
            wait = 30
        wait = min(wait + 2, 90)
        if attempt < max_retries:
            print(f"    429 rate-limited, waiting {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
    return resp


_MARKER_RE = re.compile(r"[\[【（(][^\]】）)]*[\]】）)]")


def _plain_preview(text: str) -> str:
    """去掉 [中文指令]/（动作）等标记,给设计端点用纯净样句。

    设计端点的 previewText 只是生成音色的样本句;带方括号情绪标记会 500
    (ERR_VOICE_DESIGN_FAILED)。情绪标记留给后续 TTS 合成阶段用。
    """
    stripped = _MARKER_RE.sub("", text)
    return re.sub(r"\s+", "", stripped).strip()


def _persona_meta(p: dict) -> dict:
    return {"key": p["key"], "name": p["name"], "prompt": p["prompt"]}


def _ext_from_ctype(ctype: str) -> str:
    if "mpeg" in ctype or "mp3" in ctype:
        return "mp3"
    if "wav" in ctype:
        return "wav"
    return "bin"


def _extract_candidates(design: dict) -> list[dict]:
    """文档字段:designId + candidateId + previewAudioUrl。兼容单/复数与大小写。"""
    if isinstance(design.get("candidates"), list):
        raw = design["candidates"]
    else:  # 单候选:字段平铺在顶层
        raw = [design]
    out = []
    for c in raw:
        cid = c.get("candidateId") or c.get("candidate_id") or c.get("id")
        if cid:
            out.append({"candidateId": cid, "previewAudioUrl": c.get("previewAudioUrl")})
    return out


def cmd_generate(client: httpx.Client, only: str | None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    personas = [p for p in PERSONAS if not only or p["key"] == only]
    if not personas:
        print(f"no persona matched key={only!r}", file=sys.stderr)
        sys.exit(2)

    for i, p in enumerate(personas):
        if i > 0:
            time.sleep(3)  # 人设间隔,缓解限流
        print(f"[design] {p['key']} ({p['name']}) ...", flush=True)
        payload = {
            "prompt": p["prompt"],
            "previewText": _plain_preview(p["preview_text"]),
            "providers": ["fishaudio"],
        }
        resp = _post_with_retry(
            client, "/voice-designs", payload, f"design-{p['key']}"
        )
        if resp.status_code >= 300:
            print(f"  FAILED {_fmt_err(resp)}", file=sys.stderr)
            manifest.append({**_persona_meta(p), "error": _fmt_err(resp)})
            continue
        design = resp.json()
        design_id = design.get("designId") or design.get("design_id")
        candidates = _extract_candidates(design)
        print(f"  designId={design_id} candidates={len(candidates)}")

        cand_records = []
        for idx, cand in enumerate(candidates):
            rec = _download_candidate(client, design_id, cand, p["key"], idx)
            rec["chosen"] = idx == 0  # 默认选第一个,听完可改
            cand_records.append(rec)
        manifest.append(
            {**_persona_meta(p), "design_id": design_id, "candidates": cand_records}
        )

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nmanifest -> {MANIFEST_PATH}")
    print("听完试听后,编辑 manifest 把满意候选的 chosen 设为 true(每个 persona 仅一个),再跑 save。")


def _download_candidate(
    client: httpx.Client, design_id: str, cand: dict, key: str, idx: int
) -> dict:
    """GET /voice-designs/{id}/candidates/{cid}/audio -> 音频二进制。"""
    cid = cand["candidateId"]
    rec: dict = {"candidate_id": cid, "file": None}
    r = client.get(f"/voice-designs/{design_id}/candidates/{cid}/audio")
    if r.status_code >= 300:
        print(f"    download FAILED {_fmt_err(r)}", file=sys.stderr)
        return rec
    ctype = r.headers.get("content-type", "")
    if "html" in ctype or r.content[:15].lstrip().startswith(b"<!DOCTYPE"):
        print(f"    download returned HTML not audio (ctype={ctype})", file=sys.stderr)
        return rec
    fname = f"{key}__{idx}__{cid}.{_ext_from_ctype(ctype)}"
    (OUT_DIR / fname).write_bytes(r.content)
    print(f"    saved {fname} ({len(r.content)} bytes, {ctype})")
    rec["file"] = fname
    return rec


def cmd_save(client: httpx.Client) -> None:
    """把 manifest 里 chosen 候选转成持久 voice:POST /voice-designs/{id}/voices。"""
    if not MANIFEST_PATH.exists():
        print(f"no manifest at {MANIFEST_PATH}; run generate first", file=sys.stderr)
        sys.exit(2)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    results: list[dict] = []
    for i, entry in enumerate(manifest):
        design_id = entry.get("design_id")
        chosen = [c for c in entry.get("candidates", []) if c.get("chosen")]
        if not design_id or not chosen:
            print(f"[skip] {entry['key']}: no design_id or chosen candidate", file=sys.stderr)
            continue
        cand = chosen[0]
        if i > 0:
            time.sleep(3)
        print(f"[save] {entry['key']} ({entry['name']}) cand={cand['candidate_id']} ...")
        payload = {
            "candidateId": cand["candidate_id"],
            "name": entry["name"],
            "visibility": "private",
        }
        resp = _post_with_retry(
            client,
            f"/voice-designs/{design_id}/voices",
            payload,
            f"save-{entry['key']}",
        )
        if resp.status_code >= 300:
            print(f"  FAILED {_fmt_err(resp)}", file=sys.stderr)
            continue
        body = resp.json()
        voice_id = body.get("voiceId") or body.get("voice_id") or body.get("id")
        print(f"  voiceId={voice_id}")
        results.append(
            {"key": entry["key"], "name": entry["name"], "voice_id": voice_id}
        )

    out = OUT_DIR / "saved_voices.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaved voiceIds -> {out}")
    print("把这些 voice_id 交给我,用于生成 preset_voices seed migration。")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("generate", "save"):
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    only = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--"):
            only = arg

    env = _load_env(ENV_PATH)
    api_key = os.environ.get("FISH_API_KEY") or env.get("FISH_API_KEY")
    if not api_key:
        print("FISH_API_KEY not found in env or .env", file=sys.stderr)
        sys.exit(2)

    with _client(BASE_URL, api_key) as client:
        if cmd == "generate":
            cmd_generate(client, only)
        else:
            cmd_save(client)


if __name__ == "__main__":
    main()
