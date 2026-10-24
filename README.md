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

## 무드 시안 작업 (CLI)

사진과 느낌을 주면 같은 방식으로 시안 한 장을 만드는 흐름입니다.

```sh
pip install -e .                       # edas 명령 설치
edas mood fonts --install              # Pretendard, Noto Serif KR (OFL)
edas mood list                         # 승인된 시안 목록
edas mood render match-dandy --image sources/match_spread.png   # 승인본 재현 → "identical to the approved file"
```

새 작업은 이 저장소에서 `claude`를 실행하고 그냥 말하면 됩니다. 슬래시 명령은 필요 없습니다.

> 이 사진으로 이렇게 잡지 만들어줘 (사진 첨부)
> 이 사진 부드러운 댄디 느낌으로
> 이 PDF 넣고 실제 판매 가능하게 만들어줘
> 이 슬라이드들 분위기 알아서 잡아줘

Claude는 `CLAUDE.md`의 지시에 따라 `.claude/skills/magazine/SKILL.md`를 자동으로 불러옵니다.
- **무드를 주면** 그 무드로 만듭니다.
- **무드가 없으면** `edas mood read`로 페이지마다 분위기를 측정합니다. 그다음 카피와 사진 내용, `docs/mood_library.md`를 보고 무드를 직접 고릅니다.
- **PDF가 오면** `edas mood pdf-extract`로 원본 해상도 이미지를 꺼냅니다.
- **판매용이면** `edas mood print-pdf`로 판형과 도련(재단 여유분)이 들어간 인쇄 PDF를 만들고, 이미지 해상도를 점검해 보고합니다.

승인된 시안은 `tests/test_mood_approved.py`가 원본에서 다시 렌더링해 픽셀 단위로 같은지 검사합니다. 하나라도 달라지면 테스트가 실패합니다.
