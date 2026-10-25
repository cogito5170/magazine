# 무드 작가 (mood writer): 무드 아이디어만 뽑는 쪽

윤경 님 지시(2026-10-25): "무드만 뽑는 쓰레드", "아이디어를 기계처럼 뽑고 그 다음에 작업", "GentleMonster 레포의 write agent / editor agent 협업 구조".

gentleMonster의 `synopsis.py`("The model writes; code judges")와 `engine/policy.py`(기본 REJECT, 원장)를 따른다.
작가는 `spec.json`만 쓰고 지면을 그리지 않으며 스스로 채점하지 않는다. 편집 스레드가 승인 구조로 렌더하고, 코드 심판(`edas/mood/judge.py`)이 판정한다. 우편함 규칙은 `docs/mood_relay.md`에 있다.

```sh
python3 scripts/mood_writer.py --list
python3 scripts/mood_writer.py
python3 scripts/mood_editor.py
```

## 작가가 스스로 지키는 것 (채점이 아니라 위생)

- 색만 바꾼 후보는 내지 않는다. 와비사비가 "댄디랑 똑같다"로 반려된 이유다.
- 댄디의 고유 레버를 쓰지 않는다: Richter 줄무늬 제목(`title_mode=strip`), 부드러운 JPEG 그림자(`soft_jpeg`), 슬릿스캔(`slit_amp`).
- 색칩, ΔE 숫자, 이성적 그리드, 사진 생성과 인페인팅은 쓰지 않는다.
- 카드마다 동시대 미술 기법 하나와, 이번에 실제로 열어 읽은 출처 및 인용문을 붙인다.

## 1차 제안 14개 (레버로 표현 가능, 우편함 001–014)

| # | 무드 | 기법 · 출처 | 사진 처리 | 제목 · 그림자 |
|---|---|---|---|---|
| 001 | 청사진: 네 장소를 프러시안 블루 한 톤으로 맞춘 표본 | [Anna Atkins, Photographs of British Algae (1843), cyanotype photograms](https://aperture.org/blog/anna-atkins/) | duotone | italic solid · none |
| 002 | 크루거: 흑백 사진 위 빨간 띠와 굵은 기울임 고딕, 카피가 선언처럼 | [Barbara Kruger, black-and-white photographs with white-on-red Futura Bold Oblique](https://whitney.org/artists/2635) | duotone | inter solid · none |
| 003 | 프로보크: 거칠고 흔들리고 초점 나간 흑백, 갱지 | [Daido Moriyama / Provoke (late 1960s), are-bure-boke](https://thephotographersgallery.org.uk/node/2317) | duotone, blur_ramp | sans solid · threshold |
| 004 | 폴케: 신문 망점을 크게 키워 사진이 점으로 풀리는 지면 | [Sigmar Polke, Rasterbilder (1960s), magnified newsprint dots](https://en.wikipedia.org/wiki/Sigmar_Polke) | halftone | inter outline · none |
| 005 | 바인가르트: 리스 필름을 겹친 듯 반전과 거친 망점, 시안 별색 | [Wolfgang Weingart, layered film collages with rough halftone screens (Basel, 1970s-80s)](https://eyeondesign.aiga.org/museum-of-design-zurich-unveils-the-weingart-archive/) | solarize, halftone | inter outline · threshold |
| 006 | 습판: 어두운 금속판 위 은빛 단색, 가운데만 선명하고 가장자리는 흐름 | [Sally Mann, Proud Flesh (2009), wet-plate collodion with its flaws kept](https://brooklynrail.org/2009/11/artseen/sally-mann-proud-flesh/) | duotone, blur_ramp | italic solid · none |
| 007 | 가와우치: 과노출로 들뜬 파스텔, 하얀 지면, 가는 글자 | [Rinko Kawauchi, Utatane (2001), pastel shift and square format](https://cphmag.com/rinko-kawauchis-world-of-wonders/) | tone | inter solid · none |
| 008 | 홀저: 알루미늄 판 위 앰버 LED, 카피가 전광판 문장처럼 | [Jenny Holzer, Truisms on LED signs](https://en.wikipedia.org/wiki/Jenny_Holzer) | duotone, scanlines | inter solid · none |
| 009 | 백남준: 나무 TV 함 안의 CRT, 주사선과 RGB 번짐, 형광 빛 | [Nam June Paik, The More, The Better (1988), 1,003 CRT monitors](https://en.wikipedia.org/wiki/The_More,_The_Better) | misregister, scanlines | inter outline · none |
| 010 | 펑크 진: 복사기로 1비트가 된 사진, 토너 얼룩, 굵은 고딕 | [Sniffin' Glue (1976), cut-and-paste, typewritten, photocopied fanzine](https://www.udiscovermusic.com/stories/40-years-ago-our-first-whiff-of-sniffin-glue) | threshold | sans solid · threshold |
| 011 | 라우센버그: 용제로 옮긴 흐린 사진, 빗금 질감, 붉은 과슈 | [Robert Rauschenberg, Thirty-Four Illustrations for Dante's Inferno (1958-60), solvent transfer](https://www.moma.org/collection/works/36730) | dither, blur_ramp | italic outline · none |
| 012 | 단색화 묘법: 한지에 스며든 듯 아주 옅은 사진, 흑연 회색, 반복과 시간 | [Park Seo-Bo, Écriture (Myobop), pencil lines on wet layers of hanji](https://m.kukjegallery.com/exhibition/234) | blur_ramp | sans outline · none |
| 013 | 사바티에: 현상 중 빛을 켠 사고, 밝고 어두움이 뒤집힌 은빛 윤곽 | [Lee Miller / Man Ray, solarisation (Sabatier effect), Paris c.1929](https://www.leemillerresearchguide.com/articles/blog-post-title-four-a6392) | solarize, duotone | inter outline · ruff |
| 014 | 에어로크롬: 적외선 필름처럼 올리브 재킷이 마젠타로 뒤집힌 낯선 색 | [Richard Mosse, The Enclave (2013), Kodak Aerochrome infrared film](https://www.unsw.edu.au/newsroom/news/2014/03/infrared-film-captures-congo-war) | duotone | serif solid · ruff |

## 2차 제안 8개: 레이아웃까지 바꾼다 (우편함 015–022)

윤경 님 피드백(2026-10-25): "레이아웃은 그대론데?", "지난 세션에서는 무드 바꾸면 다 바꿨는데". 이제 무드는 지면 전체를 다시 설계하는 단위다. 모든 새 카드에 `structure`(배치, 제목, 사진 자리)를 넣는다. 승인작 3장과 그 함수는 건드리지 않고, 편집 스레드가 새 함수로 렌더한다.

| # | 무드 | 레이아웃 | 기법 · 출처 |
|---|---|---|---|
| 015 | 스테자커: 같은 사람의 두 장소를 반씩 이어, 한 몸이 두 장소의 옷을 입는다 | splice | [John Stezaker, spliced found portraits (Marriage series)](https://www.npg.org.uk/whatson/display/2019/john-stezaker-portrait) |
| 016 | 조각보: 네 장소 사진을 조각으로 잘라 솔기로 이은 한 장의 보자기 | jogakbo | [jogakbo, Korean patchwork wrapping cloth of leftover scraps](https://www.vam.ac.uk/articles/jogakbo-traditional-korean-patchwork) |
| 017 | 호크니 조이너: 한 장면을 겹친 조각 수십 장으로 다시 모은 시선의 모자이크 | joiner | [David Hockney, joiners (photocollage, 1980s)](https://www.h2g2.com/edited_entry/A520840) |
| 018 | 소피 칼: 액자 속 흑백 사진과 타자 원고 패널, 기록처럼 | panel | [Sophie Calle, photographs paired with framed text panels](https://en.wikipedia.org/wiki/Sophie_Calle) |
| 019 | 크리스토퍼 울: 오른쪽 면 전체를 덮는 검정 스텐실 MAT / CH. | stencil_title | [Christopher Wool, word paintings in black stencilled letters](https://en.wikipedia.org/wiki/Christopher_Wool) |
| 020 | 발데사리: 얼굴 자리에 원색 점, 점 색은 그 장소 옷의 톤 | dots | [John Baldessari, coloured dots over faces in found press photographs (1985-)](https://www.kcur.org/2013-03-12/for-john-baldessari-conceptual-art-means-serious-mischief) |
| 021 | 데이비드 카슨: 그리드 없이 글과 사진이 겹치고 자간이 벌어진다 | nogrid | [David Carson, Ray Gun (1990s)](https://www.aiga.org/membership-community/aiga-awards/2014-aiga-medalist-david-carson) |
| 022 | 크루거: 한 장면이 양면을 덮고, 제목과 카피가 빨간 띠로 가로지른다 | bars | [Barbara Kruger, black-and-white photographs with white-on-red Futura Bold Oblique](https://whitney.org/artists/2635) |

픽셀 소팅(Asendorf)은 댄디 슬릿스캔 줄무늬와 같은 계열이어서 뺐다.
## 판정 결과

편집 스레드가 각 폴더에 `response.json`과 `preview.jpg`를 쓰고, 저장소 `docs/mood_ledger.jsonl`에 남긴다. 작가는 다음 제안을 만들 때 거절 이유를 읽고 같은 실수를 반복하지 않는다.

## 3차부터: 승인 레시피를 같이 적는다

2차 렌더를 윤경 님이 "과감함이나 낯설게하기도 없고 정제도 안 되어 있고"라며 반려했다. 편집 쪽은 모든 kind가 `edas/mood/kinds/recipe.py`를 거치게 고쳤다. 작가는 3차 카드부터 spec 최상위에 두 가지를 반드시 적는다. 빠지면 `lint`가 카드를 보내지 않는다.

- `defamiliarize`: 낯설게하기 장치 하나
- `techniques`: 승인 팔레트 기법 2~3개
- `structure`: 레이아웃

## 사용자 반응

- 2026-10-25: **022 크루거 빨간 띠** 표지(2차 렌더, recipe 적용 전 판)에 윤경 님이 "이건 좋아"라고 했다. 흑백 풀블리드 사진, 빨간 띠 제목, 빨간 테두리 프린트, 카피 띠로 구성된 판이다.
