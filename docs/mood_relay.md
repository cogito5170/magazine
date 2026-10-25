# mood-relay — write(무드 작가) ↔ editor(지면 편집) 우편함

gentleMonster 의 compose ↔ judge 구조를 옮긴 것. **작가는 스스로 채점하지 않는다. 심판은 코드다. 기본은 REJECT. 거절도 원장에 남는다.**

## 작가(무드 스레드)가 하는 일
- 제안 하나 = 폴더 하나: `/mnt/project-files/mood-relay/<NNN>-<짧은-이름>/spec.json` (번호는 기존 다음 번호).
- 지면을 그리지 않는다. `spec.json` 만 쓴다:

```json
{"name": "risograph zine", "mood": "한 줄 해석", "sources": ["실제로 확인한 출처 URL"],
 "layer": {"paper": [242,238,228], "ink": [40,52,120], "taupe": [232,120,150], "camel": [40,52,120],
           "title_face": "inter", "title_weight": "Black", "title_mode": "solid", "title_color": [236,92,128],
           "hero_fx": [["duotone", [40,52,120], [242,238,228]], ["misregister", 4]],
           "print_fx": [["halftone", 4, [40,52,120]]], "shadow": "threshold", "caption_face": "mono", "marks": true,
           "body_face": "sans", "body_weight": "Regular"}}
```

### layer 에 쓸 수 있는 키 (그 밖의 키는 거절)
- 색: `paper` `ink` `taupe`(그림자·괘선) `camel`(캡션) `light` `note` — RGB 배열
- 서체: `title_face` serif|sans|inter|italic, `title_weight` (Thin…Black), `title_mode` strip|solid|outline, `title_color`,
  `body_face` serif|sans, `body_weight`, `caption_face` serif_it|mono
- 사진 처리: `hero_fx`, `print_fx` = 연산 목록. `["duotone", lo, hi]` `["halftone", cell, ink]` `["dither", ink, cell]`
  `["threshold", t]` `["scanlines"]` `["misregister", dx]` `["blur_ramp", r]` `["solarize", t]`
- 그 밖: `shadow` soft_jpeg|ruff|threshold|none, `marks` true|false, `saturation`, `tone` [lo, hi, amount],
  `halation` [thr, radius, tint, strength], `hero_matte` / `print_matte` [black, white], `slit_amp`, `print_blur`,
  `strip_key` night|park|shop|rock, `strip_col` [x, y0, y1], `strip_mix`, `stages`, `grain`
- `structure` 블록이 없으면 승인 NOCTURNE 구조에 위 레버만 얹는다(`layer.structure` 로 lineup|wild|eyeline 도 고를 수 있다).

### structure 블록 = 무드마다 배치까지 새로 짠다
무드를 바꾸면 레이아웃·서체·처리 전부 바뀐다. `"structure": {"kind": "<kind>", ...}` 를 쓰면
`edas/mood/kinds/<kind>.py` 의 `render(crops, texts, layer, persons, H) -> (page, spec)` 가 그린다
(spec: `text_boxes`, `photo_boxes`, `texts_set`, 사진 위 글자는 `panels`). 현재 kind:
splice · jogakbo · joiner · panel · stencil_title · dots · nogrid · bars. 새 kind 는 새 파일로만 추가한다.
표지에도 같은 kind 를 쓴다(`texts["cover"]` 가 참). 사진은 자르기·확대·회전·반전·톤만 한다.
구조가 달라도 **승인 레시피는 그대로 들어간다** (`edas/mood/kinds/recipe.py`, 값은 승인작과 동일):
과감한 제목(제목 상자 ≥ 지면의 4.5%, 승인작 실측 4.6~8.5%) · Richter 줄무늬 제목 · 원본 크기·확대율 표기 ·
승인 팔레트 기법 2~3개 · 낯설게하기 장치 하나 · 마감 프레임(러닝헤드, 공정 두 줄, 폴리오).
사용자: "과감함이나 낯설게하기도 없고 정제도 안 되어 있고" (작가 기법만 옮긴 판은 반려).

## 편집(이 스레드)이 하는 일
`python3 scripts/mood_editor.py` 가 응답 없는 폴더를 렌더(표지+펼침면)하고 재서 `response.json` · `preview.jpg` 를 쓴다.

### 심판 (edas/mood/judge.py)
- V 불변조건(하나라도 실패하면 REJECT): 승인작 3장이 각자의 함수로 픽셀 동일 · 카피가 지면 안·사진 밖
  (사진 위라면 측정된 단색 띠 위, 띠와 글자 대비 ≥ 4.5) · 카피 원문 그대로 · 본문 대비 ≥ 4.5, 캡션 ≥ 3
- J 레버에 `layout` 추가: 사진 면적이 match-dandy 배치와 겹치는 비율(IoU) ≤ 0.55 이면 레버 하나로 센다.
- `recipe`·`bold`: 위 레시피를 따랐는지, 제목이 과감한지. 얼굴을 가리는 등 규칙상 사용자 확인이 필요한 kind 는 통과해도 HOLD.
- J: 승인 무드(댄디·검정·라포)와의 지면 평균 색차 최소값 ≥ 20 (사용자가 "댄디랑 똑같다"고 한 와비사비 = 4.2, 승인작끼리 최소 33.4),
  팔레트 말고 바꾼 레버 ≥ 2
- 거절된 이유를 읽고 다음 제안에서 같은 실수를 반복하지 않는다. 원장: 저장소 `docs/mood_ledger.jsonl`.
- 불변조건을 통과한 지면은 ACCEPT 가 아니라 **PENDING** 이다. 정전 비평 앙상블이 최종 판정한다 (아래).

### 정전 비평 앙상블 (심판의 최종 판정, 2026-10-25)
윤경 님 규칙: "무조건 지금 심판의 말을 따른다. 대신 심판의 박사급 시각디자이너 이론을 적용하도록 한다." 그래서 심판의 마지막 단계는 코드가 못 하는 미적 판정을 정전과 이론으로 한다.
- 기준: `docs/canon/aesthetic_criteria.md` (정전 37건, 이미지 67장에서 뽑은 주도 장치 7유형과 절제 규칙). 보드: `docs/canon/board.json`.
- 묶음(`<제안>/critic/`): 시안, 색·배치 기술자로 찾은 가장 가까운 정전 3장, 제목과 거터의 2배 확대 크롭, 측정값(네거티브 스페이스 비율, 시선 경쟁 영역 수, 팔레트 수)과 정전 분포, 기준, `prompt.md`.
- 비평가는 서로 독립이다: Claude 세션(`critique_claude.json`), GPT(`scripts/gpt_critic.py` 로 effiency relay 경유, `critique_gpt.json`). 축마다 절대 등급이고, 기계끼리 둘 중 하나를 고르게 하지 않는다.
- 판정(`python3 scripts/mood_critic.py --record <제안>`): 유효한 비평 2개 이상, 과반이 pass, 주도 장치 합의, 핵심 축(주도 장치 명료성·절제·익숙함·안정) 중앙값이 보통 이상, 핵심 축에서 비평가 차이 1단계 이하. 하나라도 어기면 REJECT.
- 검증(`python3 scripts/validate_critic.py --build`, `--report`): 정전(자기 자신은 참고에서 제외)과 승인작 3장은 양성, 윤경 님이 반려한 시안 14장은 음성. 균형 정확도, ROC AUC, 비평가 간 가중 카파를 `docs/canon/validation_report.json` 에 남긴다. 검증을 통과하기 전에는 비평가 기준을 확정하지 않는다.
- 작가 카드에 `dominant_device` 를 적으면 정전 장치 목록(`edas/mood/canon.py` `DEVICES`) 안에 있어야 한다.
- 윤경 님이 고른 결과는 `python3 scripts/editor_pick.py` 로 `docs/judgement_ledger.jsonl` 에 승자·패자 쌍으로 남긴다. 비평가 보정용 근거 데이터다.
