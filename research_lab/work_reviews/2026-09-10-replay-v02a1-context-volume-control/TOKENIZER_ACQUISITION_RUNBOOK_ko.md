# Replay v0.2A.1 공식 Tokenizer Acquisition Runbook

이 continuation은 기존 `preflight_result.json`을 수정하지 않는다. 새 evidence는
`acquisition_runs/official-pinned-001/` 아래에 append-only로 기록한다.

## 고정 계약

- 모델 저장소: `Qwen/Qwen3.5-122B-A10B`
- Python package: `transformers==5.16.1`, `tokenizers==0.23.2`
- package index: `https://pypi.org/simple`
- acquisition attempt: 정확히 1회
- historical exact gate: sanitized `4,903`, original `14,387`
- gate 실패 시 다른 version/tokenizer/template/provider count endpoint를 시도하지 않음
- gate 성공 시에만 S-short와 S-long-control을 각각 1회 실행, retry 0

## 격리와 provenance

Runner는 repository 밖 `.experiments/replay-v02a1-official-pinned-001/`에 새 venv,
wheel cache, tokenizer snapshot을 만든다. GitHub에는 package 및 tokenizer asset의
identity, immutable revision, filename, SHA-256, canonical locator만 기록하며 asset이나
model weight 자체는 commit하지 않는다.

Package는 먼저 official PyPI에서 exact pins와 resolver-selected transitive wheels를
download하고, 설치는 `--no-index`로 수행한다. Tokenizer asset 획득 후 count와 input
generation은 `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `local_files_only=True`,
`trust_remote_code=False`, `use_fast=True`로 수행한다.

## 실행

branch 최신 preparation commit을 fast-forward한 뒤 task directory에서 실행한다.

```bash
python3 acquire_once_and_continue.py
```

Runner는 terminal blocked evidence 또는 sealed gate/evidence를 review feature branch에
push한다. main merge, deploy, methodology/adoption 변경은 수행하지 않는다.
