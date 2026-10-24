# EDAS — 수학적 에디토리얼 디자인 분석 시스템

잡지·포트폴리오 PDF의 구성 요소를 측정하여 수학적 특징 벡터로 변환하고, 레퍼런스와 비교하며,
근거가 기록된 수정 제안을 만드는 Python 소프트웨어입니다.

**원칙**

- 측정값(`measured`), 규칙 기반 추정값(`estimated`), 학습 기반 예측값(`predicted`)을 구분합니다.
- 측정하지 못한 값은 `null`로 남기고 이유를 적습니다.
- 미적 판단은 가설로 취급합니다. 검증된 인간 선호 모델이 없으면 출력하지 않습니다.
- 크기·대비·정렬·채도·폰트 수·여백을 미감 점수로 대신하지 않습니다.
- 원본 PDF는 수정하지 않습니다.
- 수정 제안은 근거 기록과 사용자 승인이 있어야 하며, 보호 페이지는 변경 대상에서 제외됩니다.

## 설치와 실행

```bash
pip install -e .            # numpy, pydantic, pypdfium2, pillow, pyyaml, reportlab
python -m edas analyze PORTFOLIO.pdf -o output --protect 2
python -m edas typo-experiment PORTFOLIO.pdf --page 3 --text Observe --alt /path/FontA.ttf /path/FontB.ttf -o output/typo
python -m edas ab-page output/typo/experiment_A/manifest.json -o output/ab_A.html --page-id "<sha>:p3"
python -m edas prefs-import judgments-r1-A_typeface.json --store data/judgments.jsonl
python -m edas prefs-report --store data/judgments.jsonl --original AesthetNova-Bold
python -m edas regress ORIGINAL.pdf CANDIDATE.pdf --protect 2
python -m edas profile-build ref1.pdf ref2.pdf --style minimalist_magazine -o profiles/minimal.json
python -m edas specs -o specs.json      # D,U,F,N,T,E,C,V for every parameter
python -m unittest discover -s tests -t .
```

`analyze` produces:

- `*.analysis.json`: every parameter in the §14 schema;
- `*.parameters.csv`;
- `*.report.html`: grid/bbox overlays, saliency heatmaps, rhythm charts and proposals;
- `*.report.pdf`;
- `*.proposals.json`: approval-pending change proposals.

## Structure

| Path | Role |
|---|---|
| `edas/pdf/` | PDFium extraction, coordinate unification, layout objects, raster fallback |
| `edas/mathcore/` | geometry, statistics, colour (CIEDE2000), image operators, saliency, glyph geometry |
| `edas/modules/` | A layout, B typography, BK Korean–Latin, typeface dimensions (TA–TX), C photography, D composition, E rhythm, F aesthetics |
| `edas/typo/` | glyph outlines, morphology, optical spacing, font catalogue (licences), candidates, counterfactual experiments |
| `edas/preference/` | judgment schema, Bradley–Terry models, validation, A/B interface |
| `edas/governance/` | evidence records, approval gate, regression comparison |
| `edas/reference/`, `edas/evaluation/`, `edas/optimize/`, `edas/report/` | profiles, Q vectors, proposals and simulation, exports |
| `docs/` | `status.md` (what is and is not implemented), `spec_issues.md`, `postmortems/` |

## Status

See `docs/status.md`. `PORTFOLIO 5.pdf` is not in this repository, so the first-target analysis has not
been run. All tests use synthetic PDFs with known answers.
