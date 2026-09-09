
#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, getpass, json, os, random, re, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any, Dict, List

import run as core
import topology_benchmark as tb

ROOT = Path(__file__).resolve().parent
VERSION = "0.8.1"
DEFAULT_CASES = ["hard-003","hard-005","hard-006"]
CRITICS = ["122b","397b","glm320","ds284"]

def dumps(x): return json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True)

def safe(s): return re.sub(r"[^A-Za-z0-9_.-]+","_",s)

def write_json(path: Path, obj: Any):
    path.write_text(dumps(obj), encoding="utf-8")
    path.chmod(0o600)

def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)

def outdir():
    root = ROOT/"overnight_results"
    root.mkdir(mode=0o700, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=dt.datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=str(root)))

def call(label, model, messages, token, max_tokens, seed, timeout):
    meta = core.MODELS[model]
    payload = core.request_for(meta["id"], messages, max_tokens, True, seed)
    t0=time.monotonic()
    raw=core.post_json(payload, token, timeout)
    result=core.sanitize_response(raw, meta["id"], token)
    elapsed=round(time.monotonic()-t0,3)
    usage=result.get("usage",{})
    cost=0.0
    if "prompt_tokens" in usage and "completion_tokens" in usage:
        cost=(usage["prompt_tokens"]*meta["input"]+usage["completion_tokens"]*meta["output"])/1e6
    return {"label":label,"model_key":model,"requested_model":meta["id"],
            "result":result,"wall_seconds":elapsed,"nominal_cost_usd_from_usage":cost}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    ap.add_argument("--critics", nargs="+", default=CRITICS)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--seed", type=int, default=20260905)
    ap.add_argument("--budget-usd", type=float, default=1.00,
                    help="DeepInfra conservative local reservation cap; not provider-enforced.")
    ap.add_argument("--with-frontier", action="store_true",
                    help="After all local critics, run source-enabled Frontier blind review for each case.")
    ap.add_argument("--frontier-budget-usd", type=float, default=1.50)
    ap.add_argument("--frontier-max-output-tokens", type=int, default=4096)
    ap.add_argument("--run", action="store_true")
    args=ap.parse_args()

    for c in args.cases: core.load_case(c)
    for m in args.critics:
        if m not in core.MODELS: raise SystemExit(f"Unknown critic model key: {m}")

    # One shared 122B primary per case, then all critics see exactly the same primary.
    reserve=0.0
    for c in args.cases:
        case=core.load_case(c)
        pm=tb.primary_messages(case)
        reserve += tb.reserve(pm,"122b",args.max_tokens)
        # critic reserve estimated after placeholder candidate of reasonable size
        placeholder="후보 답변 " * 1200
        cm=tb.critic_messages(case,placeholder)
        for m in args.critics:
            reserve += tb.reserve(cm,m,args.max_tokens)

    print("Overnight family benchmark 계획")
    print("cases:", ", ".join(args.cases))
    print("critics:", ", ".join(args.critics))
    print("공유 primary: case당 122B 1회")
    print("예상 DeepInfra 호출:", len(args.cases)*(1+len(args.critics)))
    print("순차 실행 / 자동 재시도 없음 / 실패한 모델은 기록 후 다음 모델 계속")
    print(f"보수적 DeepInfra 예약 추정≈${reserve:.3f} / cap ${args.budget_usd:.2f}")
    print("with Frontier:", args.with_frontier)
    if reserve > args.budget_usd:
        raise SystemExit("예약 추정이 --budget-usd를 초과합니다. 실행하지 않았습니다.")
    if not args.run:
        print("DRY RUN 완료")
        return 0

    if input("밤샘 유료 benchmark를 실행하려면 RUN 입력: ").strip()!="RUN":
        print("취소"); return 2
    token,_=core.find_token(prompt=True)

    out=outdir()
    manifest={"version":VERSION,"created_at":dt.datetime.now(dt.timezone.utc).isoformat(),
              "cases":args.cases,"critics":args.critics,"shared_primary":"122b",
              "max_tokens":args.max_tokens,"timeout":args.timeout,
              "limitations":["synthetic calibration only","serverless proxy, not Mac runtime benchmark",
                             "different model families/serving stacks/precisions are confounded",
                             "no automatic retry; errors continue to next model"]}
    write_json(out/"manifest.json",manifest)

    local_total=0.0
    case_dirs=[]
    for ci,cid in enumerate(args.cases):
        case=core.load_case(cid)
        cdir=out/cid; cdir.mkdir(mode=0o700)
        case_dirs.append(cdir)
        print(f"\n=== {cid} ===")
        try:
            primary=call(f"{cid}/shared-primary","122b",tb.primary_messages(case),token,args.max_tokens,args.seed+ci*1000+1,args.timeout)
            write_json(cdir/"shared-primary.json",primary)
            local_total += primary["nominal_cost_usd_from_usage"]
            print(f"primary => complete | {primary['wall_seconds']}s | ${primary['nominal_cost_usd_from_usage']:.5f}")
        except Exception as e:
            write_text(cdir/"PRIMARY_ERROR.txt",str(e))
            print("primary ERROR:",str(e))
            continue

        finals={}
        for mi,model in enumerate(args.critics):
            try:
                rec=call(f"{cid}/{model}-critic",model,
                         tb.critic_messages(case,primary["result"]["answer"]),
                         token,args.max_tokens,args.seed+ci*1000+100+mi,args.timeout)
                write_json(cdir/f"{safe(model)}-critic.json",rec)
                local_total += rec["nominal_cost_usd_from_usage"]
                finals[model]=rec
                print(f"{model} critic => complete | {rec['wall_seconds']}s | ${rec['nominal_cost_usd_from_usage']:.5f}")
            except Exception as e:
                write_text(cdir/f"{safe(model)}-ERROR.txt",str(e))
                print(f"{model} ERROR:",str(e))

        # Stable blind mapping created from a deterministic shuffle.
        labels=list(finals.keys())
        rnd=random.Random(args.seed+ci)
        rnd.shuffle(labels)
        mapping={}
        for n,model in enumerate(labels,1):
            arm=f"Arm-{n:02d}"
            mapping[arm]={"critic":model}
            ans=finals[model]["result"]["answer"]
            src = tb.REVIEW_INSTRUCTION + "\n조건: 동일한 전체 evidence bundle 제공. 외부 웹 도구는 없다.\n" + dumps(case) + \
                  "\n응답상태: complete\n\n# "+arm+"\n"+ans
            write_text(cdir/f"{arm}-source-review.txt",src)
        write_json(cdir/"private-arm-map.json",mapping)

    write_json(out/"SUMMARY.json",{"local_nominal_cost_usd":round(local_total,6),
                                   "result_dir":str(out),
                                   "cases":args.cases,"critics":args.critics})
    print(f"\nLocal 완료. usage 기반 명목비용≈${local_total:.4f}")
    print("결과:",out)

    if args.with_frontier:
        # Ask OpenAI key once, keep in child-process environment only.
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            key = getpass.getpass("OpenAI API 키를 이 터미널에만 입력하세요 (화면/파일 저장 안 함): ").strip()
        if not key or any(ch.isspace() for ch in key):
            print("OpenAI key invalid; Frontier skipped.")
            return 0
        env=os.environ.copy(); env["OPENAI_API_KEY"]=key
        per_case=max(0.10, args.frontier_budget_usd/max(1,len(case_dirs)))
        for cdir in case_dirs:
            if not list(cdir.glob("Arm-*-source-review.txt")):
                continue
            print(f"\nFrontier: {cdir.name}")
            cmd=[sys.executable,str(ROOT/"frontier_review.py"),
                 "--result-dir",str(cdir),"--review-type","source",
                 "--reasoning-effort","medium",
                 "--max-output-tokens",str(args.frontier_max_output_tokens),
                 "--budget-usd",str(per_case),"--yes","--run"]
            p=subprocess.run(cmd,text=True,env=env)
            if p.returncode!=0:
                print(f"Frontier failed for {cdir.name}; continuing.")
        print("\nFrontier phase finished.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
