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
- 구조(주인공 풀블리드, 세로 Richter 제목, 프린트 3장, 세로쓰기)는 승인 구조라 바꿀 수 없다. 무드는 위 레버로만.

## 편집(이 스레드)이 하는 일
`python3 scripts/mood_editor.py` 가 응답 없는 폴더를 렌더(표지+펼침면)하고 재서 `response.json` · `preview.jpg` 를 쓴다.

### 심판 (edas/mood/judge.py)
- V 불변조건(하나라도 실패하면 REJECT): 승인 구조 기계가 match-dandy 와 픽셀 동일 · 카피가 지면 안·프린트 밖 · 본문 대비 ≥ 4.5, 캡션 ≥ 3
- J: 승인 무드(댄디·검정·라포)와의 지면 평균 색차 최소값 ≥ 20 (사용자가 "댄디랑 똑같다"고 한 와비사비 = 4.2, 승인작끼리 최소 33.4),
  팔레트 말고 바꾼 레버 ≥ 2
- 거절된 이유를 읽고 다음 제안에서 같은 실수를 반복하지 않는다. 원장: 저장소 `docs/mood_ledger.jsonl`.
- ACCEPT 는 "볼 만한 후보"라는 뜻일 뿐이다. 최종 취향 판단은 사용자가 한다.
