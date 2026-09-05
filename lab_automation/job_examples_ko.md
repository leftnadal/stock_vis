# Cross-Lab Job Examples v0.1

## Math Lab

```yaml
job_id: SV-JOB-M001
lab: math_lab
goal: DailyPrice readiness probe
branch: math-lab/data-eligibility-v0.1
authority_refs:
  - math_lab/00_foundation/foundation_ko.md
  - math_lab/01_operating_system/operating_model_ko.md
allowed_write_paths:
  - math_lab/
  - lab_automation/runs/SV-JOB-M001/
db_access: read_only
expected_outputs:
  - report
  - tests
  - data_gap_proposals
```

## Research Lab

```yaml
job_id: SV-JOB-R001
lab: research_lab
goal: Investigate a new Research Trigger and produce a bounded candidate synthesis
branch: research-lab/job-r001
authority_refs:
  - research_lab/00_foundation/
  - research_lab/01_methodology/
allowed_write_paths:
  - research_lab/
  - lab_automation/runs/SV-JOB-R001/
db_access: none
expected_outputs:
  - research_report
  - evidence_refs
  - unresolved_gaps
```

## Design Lab

```yaml
job_id: SV-JOB-D001
lab: design_lab
goal: Stress-test one decision-support representation against defined personas
branch: design-lab/job-d001
authority_refs:
  - design_lab/00_foundation/
  - design_lab/01_operating_system/
allowed_write_paths:
  - design_lab/
  - lab_automation/runs/SV-JOB-D001/
db_access: none
expected_outputs:
  - design_report
  - stress_test_results
  - recommendation
```

## Cross-Lab lineage

Job은 다른 Job을 parent로 참조할 수 있다.

```text
SV-JOB-R014  Research Understanding
    -> SV-JOB-M022  Math operationalization
    -> SV-JOB-R031  mechanism follow-up
```

Parent linkage는 authority transfer를 의미하지 않는다. recipient Lab은 자신의 authority와 methodology에 따라 결과를 다시 평가한다.
