#!/usr/bin/env python3
"""StockVis multi-agent topology benchmark.

Compares single-pass and multi-pass local topologies on the same synthetic case.
Standard library only. Actual DeepInfra calls require --run and interactive RUN.

Arms:
  122-single              : 122B single analysis
  397-single              : 397B single analysis
  122-122-critic          : 122B analysis -> independent 122B critic/revision
  122-397-critic          : 122B analysis -> 397B critic/revision
  ind-122-122-synth       : independent 122B + 122B -> fixed 122B synthesis
  ind-122-397-synth       : independent 122B + 397B -> fixed 122B synthesis

The goal is to separate:
- "second pass helps" from
- "397B specifically helps" from
- "independent model diversity helps".
"""
from __future__ import annotations

import argparse, datetime as dt, getpass, json, os, random, re, sys, tempfile, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import run as core

VERSION = "0.8.0"
ROOT = Path(__file__).resolve().parent

ARM_ORDER = [
    "122-single",
    "310-single",
    "397-single",
    "122-122-critic",
    "122-310-critic",
    "122-397-critic",
    "ind-122-122-synth",
    "ind-122-310-synth",
    "ind-122-397-synth",
]

CRITIC_SYSTEM = """당신은 StockVis Research Lab의 독립 Critic이다.
아래에는 동일 evidence bundle과 1차 후보 답변이 있다.
후보를 권위로 취급하지 말고 evidence로 다시 검증한다.
후보의 framing에 고정되지 말고, 중대한 누락·잘못된 연결·scope/기간 오류·
Unsupported/Unknown/Unassessed/Contradicted 혼동·premature closure를 찾는다.
필요하면 후보 결론을 유지, 수정 또는 철회한다.
외부 사실을 만들지 않는다. 내부 사고과정 전문 대신 검증 가능한 근거 설명을 쓴다.

출력:
1. Critic이 발견한 material issue
2. 수정된 연구 결과
3. 아직 남은 Unknown/Unassessed
4. Frontier가 필요하다고 판단하는지와 이유
"""

SYNTH_SYSTEM = """당신은 StockVis Research Lab의 Synthesis Lead다.
두 독립 분석은 모두 후보일 뿐 권위가 아니다.
동일 evidence bundle을 기준으로 둘의 공통점·유용한 불일치·각각의 누락과
과잉추론을 비교하여 하나의 더 나은 연구 package를 만든다.
다수결하지 말고 evidence와 inferential soundness를 우선한다.
한 분석에만 있는 아이디어도 근거가 있으면 보존하고, 둘 다 놓친 문제도
evidence에서 발견되면 추가한다.
외부 사실을 만들지 않는다.

출력:
1. 핵심 질문과 구조
2. 보존할 material evidence/관계
3. 수정된 잠정 평가
4. 남은 Unknown/Unassessed
5. Frontier가 필요하다고 판단하는지와 이유
"""

REVIEW_INSTRUCTION = core.REVIEW_INSTRUCTION

class TopologyError(Exception):
    pass

def dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True)

def write(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as f:
        f.write(text)
    path.chmod(0o600)

def outdir() -> Path:
    root = ROOT / "topology_results"
    root.mkdir(mode=0o700, exist_ok=True)
    prefix = dt.datetime.now().strftime("%Y%m%d-%H%M%S-")
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(root)))

def model_key(model_key: str) -> Dict[str, Any]:
    return core.MODELS[model_key]

def call_model(model: str, messages: List[Dict[str, str]], token: str,
               max_tokens: int, seed: int, timeout: int) -> Tuple[Dict[str, Any], float, float]:
    meta = model_key(model)
    payload = core.request_for(meta["id"], messages, max_tokens, True, seed)
    started = time.monotonic()
    raw = core.post_json(payload, token, timeout)
    result = core.sanitize_response(raw, meta["id"], token)
    elapsed = round(time.monotonic() - started, 3)
    usage = result.get("usage", {})
    cost = 0.0
    if "prompt_tokens" in usage and "completion_tokens" in usage:
        cost = (usage["prompt_tokens"]*meta["input"] + usage["completion_tokens"]*meta["output"]) / 1e6
    return result, elapsed, cost

def primary_messages(case: Dict[str, Any]) -> List[Dict[str, str]]:
    return core.messages_for("compare", case)

def critic_messages(case: Dict[str, Any], candidate: str) -> List[Dict[str, str]]:
    user = {
        "case": case,
        "candidate_answer": candidate,
        "task": "후보를 독립적으로 비판하고 evidence에 근거해 수정된 연구 package를 만들어라."
    }
    return [{"role":"system","content":CRITIC_SYSTEM},{"role":"user","content":dumps(user)}]

def synth_messages(case: Dict[str, Any], a: str, b: str) -> List[Dict[str, str]]:
    user = {
        "case": case,
        "analysis_A": a,
        "analysis_B": b,
        "task": "두 독립 분석을 evidence 기준으로 합성하라."
    }
    return [{"role":"system","content":SYNTH_SYSTEM},{"role":"user","content":dumps(user)}]

def reserve(messages: List[Dict[str,str]], model: str, max_tokens: int) -> float:
    return core.reserve_usd(messages, max_tokens, model)

def planned_calls(case: Dict[str, Any], arms: List[str], max_tokens: int) -> List[Tuple[str,str]]:
    """Returns approximate call labels/model keys for conservative reservation."""
    calls: List[Tuple[str,str]] = []
    # No attempt to deduplicate across arms: each arm is an independent experimental run.
    for arm in arms:
        if arm == "122-single":
            calls += [(arm+"/primary","122b")]
        elif arm == "310-single":
            calls += [(arm+"/primary","310b")]
        elif arm == "397-single":
            calls += [(arm+"/primary","397b")]
        elif arm == "122-122-critic":
            calls += [(arm+"/primary","122b"),(arm+"/critic","122b")]
        elif arm == "122-310-critic":
            calls += [(arm+"/primary","122b"),(arm+"/critic","310b")]
        elif arm == "122-397-critic":
            calls += [(arm+"/primary","122b"),(arm+"/critic","397b")]
        elif arm == "ind-122-122-synth":
            calls += [(arm+"/A","122b"),(arm+"/B","122b"),(arm+"/synth","122b")]
        elif arm == "ind-122-310-synth":
            calls += [(arm+"/A","122b"),(arm+"/B","310b"),(arm+"/synth","122b")]
        elif arm == "ind-122-397-synth":
            calls += [(arm+"/A","122b"),(arm+"/B","397b"),(arm+"/synth","122b")]
        else:
            raise TopologyError("알 수 없는 arm: "+arm)
    return calls



def safe_label(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", label)

def load_existing_record(result_dir: Path, label: str) -> Optional[Dict[str, Any]]:
    p = result_dir / (safe_label(label) + ".json")
    if not p.exists():
        return None
    obj = json.loads(p.read_text(encoding="utf-8"))
    if obj.get("label") != label:
        raise TopologyError(f"기존 stage label 불일치: {p.name}")
    return obj

def reusable_record(rec: Optional[Dict[str, Any]]) -> bool:
    if not rec:
        return False
    result = rec.get("result") or {}
    return (
        result.get("status") == "complete"
        and result.get("model_matches_request") is True
        and isinstance(result.get("answer"), str)
        and bool(result.get("answer").strip())
    )

def load_existing_arm_map(out: Path) -> Dict[str, Dict[str, str]]:
    p = out / "private-arm-map.json"
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TopologyError(f"기존 private-arm-map.json을 읽지 못했습니다: {exc}")
    if not isinstance(obj, dict):
        raise TopologyError("기존 private-arm-map.json 형식이 잘못되었습니다.")
    return obj

def arm_to_label(existing_map: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    reverse: Dict[str, str] = {}
    for label, info in existing_map.items():
        if not isinstance(info, dict):
            continue
        arm = info.get("arm")
        if isinstance(arm, str):
            reverse[arm] = label
    return reverse

def next_arm_label(existing_map: Dict[str, Dict[str, str]]) -> str:
    used = []
    for label in existing_map:
        m = re.fullmatch(r"Arm-(\d+)", label)
        if m:
            used.append(int(m.group(1)))
    n = max(used, default=0) + 1
    return f"Arm-{n:02d}"

def export_blind_reviews(out: Path, case: Dict[str, Any], finals: Dict[str, Dict[str, Any]], seed: int) -> None:
    """
    Export final-arm prompts with stable blind labels.

    On a fresh run:
      - randomize finals deterministically and assign Arm-01, Arm-02, ...

    On resume:
      - preserve any existing arm->label mapping
      - update only the resumed arm's mapped files
      - never relabel another arm
      - never delete other arm review files
    """
    existing_map = load_existing_arm_map(out)
    reverse = arm_to_label(existing_map)

    if existing_map:
        mapping = dict(existing_map)
        ordered_items = list(finals.items())
    else:
        ordered_items = list(finals.items())
        random.Random(seed + 7711).shuffle(ordered_items)
        mapping = {}

    for arm, record in ordered_items:
        label = reverse.get(arm)
        if label is None:
            label = next_arm_label(mapping)
            mapping[label] = {"arm": arm}
            reverse[arm] = label

        ans = record["answer"]
        status = record["status"]
        body = f"\n\n# {label}\n{ans}"
        package_ctx = {"question":case["question"],"scope":case["scope"]}
        package = REVIEW_INSTRUCTION + "\n조건: Package-only. 원자료는 제공되지 않는다.\n" + dumps(package_ctx) + "\n응답상태: "+status+"\n" + body
        source = REVIEW_INSTRUCTION + "\n조건: 동일한 전체 evidence bundle 제공. 외부 웹 도구는 없다.\n" + dumps(case) + "\n응답상태: "+status+"\n" + body

        p1 = out/(label+"-package-review.txt")
        p2 = out/(label+"-source-review.txt")
        p1.write_text(package, encoding="utf-8"); p1.chmod(0o600)
        p2.write_text(source, encoding="utf-8"); p2.chmod(0o600)

    pm = out/"private-arm-map.json"
    pm.write_text(dumps(mapping), encoding="utf-8"); pm.chmod(0o600)


def main(argv: Optional[List[str]]=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default="hard-002")
    ap.add_argument("--arms", nargs="+", choices=ARM_ORDER, default=ARM_ORDER)
    ap.add_argument("--max-tokens", type=int, default=6144)
    ap.add_argument("--budget-usd", type=float, default=1.00)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--seed", type=int, default=12017)
    ap.add_argument("--env-file")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--resume-from", type=str, help="기존 topology 결과 폴더. complete stage는 재사용하고 incomplete stage만 다시 호출합니다.")
    ap.add_argument("--rerun-stage", action="append", default=[], help="완료 stage도 강제로 재실행할 label. 여러 번 지정 가능.")
    args = ap.parse_args(argv)

    if len(set(args.arms)) != len(args.arms):
        raise TopologyError("arm을 중복 지정할 수 없습니다.")
    if not 512 <= args.max_tokens <= 16384:
        raise TopologyError("max-tokens는 512~16384 범위여야 합니다.")
    if not 0 < args.budget_usd <= 10:
        raise TopologyError("budget-usd는 0~10달러 범위여야 합니다.")

    case = core.load_case(args.case)
    pmsg = primary_messages(case)

    # Conservative reservation: later critic/synth prompts are longer than primary.
    # Estimate each later prompt at ~2.2x primary bytes.
    primary_res = {m: reserve(pmsg,m,args.max_tokens) for m in ["122b","310b","397b"]}
    approx = 0.0
    for label,m in planned_calls(case,args.arms,args.max_tokens):
        mult = 1.0 if label.endswith("/primary") or label.endswith("/A") or label.endswith("/B") else 2.2
        approx += primary_res[m]*mult

    print("Topology benchmark 계획")
    print("case:", args.case)
    print("arms:", ", ".join(args.arms))
    print("예상 호출 수:", len(planned_calls(case,args.arms,args.max_tokens)), "| 동시 실행 없음 | 자동 재시도 없음")
    print("요청당 max tokens:", args.max_tokens, "| thinking: True")
    print("보수적 예약 추정: $%.4f / 실행 한도 $%.2f" % (approx,args.budget_usd))
    print("주의: 이 실험은 topology 비교이며 Mac 메모리/속도 측정이 아닙니다.")
    if approx > args.budget_usd:
        raise TopologyError("보수적 예약 추정이 예산 한도를 초과합니다.")
    if not args.run:
        print("DRY RUN 완료 — 실제 호출 없음.")
        return 0
    if not os.isatty(0) or input("유료 topology 실험을 실행하려면 RUN 입력: ").strip() != "RUN":
        print("취소했습니다. API 호출 없음.")
        return 0

    token, source = core.find_token(args.env_file, prompt=True)
    assert token
    os.umask(0o077)
    if args.resume_from:
        out = Path(args.resume_from).expanduser().resolve()
        if not out.exists() or not out.is_dir():
            raise TopologyError("--resume-from 결과 폴더를 찾지 못했습니다.")
        print("resume 폴더:", out)
    else:
        out = outdir()
    total_cost = 0.0
    records: Dict[str, Any] = {}
    finals: Dict[str, Dict[str, Any]] = {}

    def do(label: str, model: str, messages: List[Dict[str,str]], seed_off: int) -> Dict[str,Any]:
        nonlocal total_cost
        existing = load_existing_record(out, label) if args.resume_from else None
        force = label in set(args.rerun_stage)

        if reusable_record(existing) and not force:
            records[label] = existing
            result = existing["result"]
            print(label, "=> reused complete stage | prior", existing.get("wall_seconds"), "초")
            return result

        if existing and not force:
            prior = (existing.get("result") or {}).get("status")
            print(label, f"=> prior stage {prior!r}; 다시 호출합니다.")
        elif existing and force:
            print(label, "=> 강제 재실행합니다.")

        result, elapsed, cost = call_model(model,messages,token,args.max_tokens,args.seed+seed_off,args.timeout)
        rec = {"label":label,"model_key":model,"requested_model":core.MODELS[model]["id"],
               "wall_seconds":elapsed,"nominal_cost_usd_from_usage":cost,"result":result}
        records[label]=rec
        total_cost += cost

        p = out/(safe_label(label)+".json")
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(dumps(rec), encoding="utf-8")
        tmp.chmod(0o600)
        os.replace(tmp, p)

        print(label, "=>", result["status"], "|", elapsed, "초 | cost≈$%.5f" % cost)
        if result.get("model_matches_request") is not True:
            raise TopologyError(label+" 반환 모델을 확인하세요.")
        if total_cost > args.budget_usd:
            raise TopologyError("이번 실행에서 usage 기반 추정 비용이 한도를 초과해 중단했습니다.")
        return result

    for idx,arm in enumerate(args.arms):
        base = idx*20
        if arm == "122-single":
            r = do(arm+"/primary","122b",pmsg,base+1)
            finals[arm] = r

        elif arm == "310-single":
            r = do(arm+"/primary","310b",pmsg,base+1)
            finals[arm] = r

        elif arm == "397-single":
            r = do(arm+"/primary","397b",pmsg,base+1)
            finals[arm] = r

        elif arm == "122-122-critic":
            p = do(arm+"/primary","122b",pmsg,base+1)
            c = do(arm+"/critic","122b",critic_messages(case,p["answer"]),base+2)
            finals[arm] = c

        elif arm == "122-310-critic":
            p = do(arm+"/primary","122b",pmsg,base+1)
            c = do(arm+"/critic","310b",critic_messages(case,p["answer"]),base+2)
            finals[arm] = c

        elif arm == "122-397-critic":
            p = do(arm+"/primary","122b",pmsg,base+1)
            c = do(arm+"/critic","397b",critic_messages(case,p["answer"]),base+2)
            finals[arm] = c

        elif arm == "ind-122-122-synth":
            a = do(arm+"/A","122b",pmsg,base+1)
            b = do(arm+"/B","122b",pmsg,base+2)
            s = do(arm+"/synth","122b",synth_messages(case,a["answer"],b["answer"]),base+3)
            finals[arm] = s

        elif arm == "ind-122-310-synth":
            a = do(arm+"/A","122b",pmsg,base+1)
            b = do(arm+"/B","310b",pmsg,base+2)
            s = do(arm+"/synth","122b",synth_messages(case,a["answer"],b["answer"]),base+3)
            finals[arm] = s

        elif arm == "ind-122-397-synth":
            a = do(arm+"/A","122b",pmsg,base+1)
            b = do(arm+"/B","397b",pmsg,base+2)
            s = do(arm+"/synth","122b",synth_messages(case,a["answer"],b["answer"]),base+3)
            finals[arm] = s

    manifest = {
        "version":VERSION,"created_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "case_id":args.case,"arms":args.arms,"max_tokens":args.max_tokens,
        "budget_usd_estimate_only":args.budget_usd,"credential_source":source,
        "total_nominal_cost_usd_from_usage":total_cost,
        "limitations":[
            "synthetic calibration only",
            "fp4 vs fp8 confound remains",
            "topology arms have different call counts",
            "no Frontier call in this script",
            "not a Mac runtime or memory benchmark",
            "sequential critic arms may anchor on first-pass framing",
            "independent arms use 122B as fixed synthesizer",
        ]
    }
    pmf = out/"manifest.json"
    pmf.write_text(dumps(manifest), encoding="utf-8"); pmf.chmod(0o600)
    export_blind_reviews(out,case,finals,args.seed)

    summary = ["# Topology benchmark summary","",
               f"- case: {args.case}",
               f"- arms 완료: {len(finals)}",
               f"- 실제 local 호출 수: {len(records)}",
               f"- usage 기반 명목비용 합: ${total_cost:.6f}",
               "- 각 arm의 최종 산출물은 Arm-XX로 블라인드되어 Frontier review 파일로 export됨.",
               "- private-arm-map.json은 블라인드 평가자에게 주지 마세요.",
               "- 이 실험은 하드웨어 구매 결론을 자동 결정하지 않습니다.",""]
    ps = out/"SUMMARY.md"
    ps.write_text("\n".join(summary), encoding="utf-8"); ps.chmod(0o600)
    print("완료. topology 결과 폴더:", out)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TopologyError, core.ProbeError) as exc:
        print("중단:", str(exc), file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\n중단했습니다. 이미 보낸 요청은 처리·청구될 수 있습니다.", file=sys.stderr)
        raise SystemExit(130)
