# 무드 조성 기법 카탈로그 (감각 · 분위기 · 무드)

- 작성: 2026-10-24
- 수집: 웹 검색 기반 리서치. 대부분은 초록·서지 수준에서 확인했고 원문은 읽지 않았다.
- 근거 수준 표기: **VE** = 해당 연구를 검색에서 확인, **SO** = 2차 자료만, **PC** = 실무 관행(연구 미발견), **H** = 가설.
- 공통 한계: 단색칩, 단일 서체, 웹, 리테일, 영화 대상 연구를 사진·타이포·레이아웃이 결합된 잡지 스프레드에 적용하는 것은 모두 **H**다. 표본도 주로 서구권이다.
- 이 문서의 어떤 항목도 "좋은 디자인"의 규칙이 아니다. 무드의 방향을 고르는 데 쓰는 근거 목록이며, 실제 효과는 A/B 선호 데이터로만 확인한다(`edas.preference`).

## 0. 요약 표

| # | 기법 | 채널 | 파라미터 | 연관 무드 방향 | 근거 | EDAS 측정 |
|---|---|---|---|---|---|---|
| 1 | 명도·채도 | 색 | L*, C* | 명도↑ → 쾌↑, 채도↑ → 각성↑ | VE | C03, C06 |
| 2 | 색 감정 3요인 | 색 | 명도·채도·색상 | 활동성·무게·온도 | VE (공식 미확인) | – |
| 3 | 유사색 조화 | 색 | ΔH, ΔL* | 조화·안정 | VE | C18 |
| 4 | 색 연상 정서가 | 색 | 색↔대상 연상 | 선호/혐오 | VE | – |
| 5 | 색온도 | 색/빛 | b*, CCT | 따뜻함/차가움 | VE(조명) / H(사진) | Lab 평균 |
| 6 | 팔레트 절제·듀오톤 | 색 | 색 수, 채도 | 고요·통일 | PC | C08 |
| 7 | 사진 추출 팔레트 | 색 | 사진↔배경 ΔE | 일체감 | PC/H | photo_led |
| 8 | 하이키/로우키 | 빛 | L* 분포 | 경쾌 / 극적·우울 | PC | C03–C05 |
| 9 | 리프티드 블랙·매트 | 빛 | 블랙 포인트 | 부드러움·향수 | PC | – |
| 10 | 할레이션·블룸 | 빛 | 하이라이트 확산 | 몽환 | PC | – |
| 11 | 비네팅 | 빛 | 주변 감광 | 집중·친밀 | PC | – |
| 12 | 골든/블루 아워 | 빛 | 색온도·광각 | 향수 / 고요·쓸쓸 | PC | – |
| 13 | 틸-오렌지 그레이딩 | 빛/색 | 섀도·하이라이트 색상 | 영화적 | SO | – |
| 14 | 그레인·필름 | 질감 | 노이즈 진폭 | 아날로그·기억 | SO/PC | – |
| 15 | 얕은 심도·블러 | 빛 | 블러 반경 | 크기·거리 지각(VE), 친밀(PC) | VE/PC | C09 |
| 16 | 서체 페르소나 | 타이포 | 서체 계열 | 격식·친근·유희 | VE | TA01 |
| 17 | 둥근 vs 각진 글자 | 타이포 | 획 곡률 | 호감·단맛 / 날카로움 | VE (중국어 서체 재현 실패) | B09 |
| 18 | 대문자 vs 소문자 | 타이포 | case | 권위·유능 / 친근·따뜻 | VE | – |
| 19 | 손글씨체 | 타이포 | 손글씨 | 인간적 온기 | SO | – |
| 20 | 가독성(유창성) | 타이포 | 읽기 난이도 | 쉬움·호감 / 노력·무게 | VE | B10–B12 |
| 21 | 명조/고딕/손글씨 | 타이포(한글) | 부리, 굵기 | 고전·정적 / 현대·가벼움 | SO | BK03 |
| 22 | 굵기·자간·크기 대비 | 타이포 | wght, tracking | 우아·긴장·위계 | PC | B03, B10 |
| 23 | 한·영 혼용 보정 | 타이포 | 기준선·크기 비 | 정돈감 | PC | BK05–BK07 |
| 24 | 여백·간격 | 레이아웃 | 여백 비율 | 프레스티지·미적 매력 | VE (광고·리테일) | A09, A17 |
| 25 | 중앙·안쪽 배치 편향 | 레이아웃 | 피사체 위치 | 안정·자연스러움 | VE | D01 |
| 26 | 크롭·샷 스케일 | 사진 | 얼굴 면적 비 | 근접 → 각성·몰입 | VE(영화) / H(지면) | – |
| 27 | 대칭·균형 | 레이아웃 | 대칭도 | 아름다움·질서 | VE (추상 패턴) | D03–D05 |
| 28 | 그리드, 브로큰 그리드, 블리드, 페이싱 | 레이아웃 | 정렬 오차, 블리드 비율 | 질서 / 역동 | PC | A02, A03, E05 |
| 29 | 시각 복잡도·원형성 | 복잡도 | 클러터, 장르 관습 | 저복잡·고원형 → 호감 | VE (웹) | A19, D15 |
| 30 | 각성 잠재력 역U | 복잡도 | 복잡·신기성 | 중간이 쾌 | VE (결과 혼재) | A19 |
| 31 | 처리 유창성 | 복잡도 | 대비·대칭·반복 | 호감·미적 쾌 | VE (리뷰) | D14 |
| 32 | 곡선 선호 | 복잡도 | 윤곽 곡률 | 곡선 호감 / 각진 형태는 위협 | VE | – |
| 33 | 프랙털 차원 | 복잡도 | D≈1.3–1.5 | 선호·이완 | SO | mathcore.fractal |
| 34 | 종이 무게·질감 | 물성 | gsm, 표면 | 품질·진정성 | SO / 재현 실패 사례 있음 | – |
| 35 | 리소·망점·후가공 | 물성 | 망점·별색 | 수공·인디 | PC | – |
| 36 | 원형 모델·PAD | 모델 | 쾌·각성(·지배) | 무드 좌표 | VE (이론) | mood.generate |
| 37 | 주의 회복(부드러운 매혹) | 모델 | 자연·저강도 자극 | 회복·평온 | VE (이론) | – |
| 38 | 모션 이징·호흡 리듬 | 모션 | 지속시간, easing | 자연·평온 | PC/H (느린 호흡 자체는 VE) | M4 |
| 39 | 캡션·시적 카피·반복 모티프 | 서사 | 톤, 반복 | 의미·여운·친숙 | PC (반복은 VE) | E10 |

## 1. 색
- **#1 명도·채도 → 쾌·각성.** Valdez & Mehrabian(1994)은 Munsell 색칩으로 실험했다. 쾌 = .69B + .22S, 각성 = −.31B + .60S. Wilms & Oberfeld(2018)는 LED 전면 자극으로 실험했고, 채도와 명도가 높을수록 각성이 높아졌다. 즉 **명도가 각성에 주는 방향은 두 연구가 상충**한다. 한계: 단색 자극이다.
- **#2 색 감정 3요인.** Ou 외(2004) Part I은 영국·중국 표본으로 활동성·무게감·온도감 3요인을 찾았다. Part II는 두 색 조합을 평균으로 예측했다. 모델식 원문은 확인하지 못했다.
- **#3 유사색 조화.** Schloss & Palmer(2011)에서는 색상이 유사할수록 조화로 판단됐다. 반면 배경 위 '도형'으로 놓인 색은 대비가 클수록 선호됐다.
- **#4 색 연상.** Palmer & Schloss(2010, PNAS): 색 선호는 그 색에서 연상되는 대상의 정서가를 따른다.
- **#5 색온도.** 조명 연구(UNIST)의 결과다. 사진 화이트밸런스로 옮기는 것은 H.
- **#6, #7 절제 팔레트, 사진 추출 팔레트.** 연구를 찾지 못했다(PC). 유창성(#31)이나 저복잡도(#29)와 연결하는 것은 H.

## 2. 빛과 톤 (사진)
- **#8–#13 하이키/로우키, 매트, 블룸, 비네팅, 골든·블루 아워, 틸-오렌지.** 실무 관행이며, 통제된 선호 실험은 찾지 못했다.
- **#14 그레인.** 영화학 논문 수준의 분석만 있다(SO).
- **#15 블러.** Held 외(2010): 블러 패턴이 지각되는 크기와 거리를 바꾼다(VE). 친밀감 효과는 관행이다.
- **계산 기반 감성 특징.** Machajdik & Hanbury(2010): 색·질감·구도로 이미지 감정을 분류했다.

## 3. 타이포그래피
- **#16 서체 페르소나.** Brumberger(2003)는 독자가 서체와 텍스트에 성격을 부여함을 보였다. Shaikh, Chaparro & Fox(2006)는 20개 서체를 15개 형용사 쌍으로 평정했다.
- **#17 둥근 vs 각진.** Velasco 외(2015)는 둥근 서체가 단맛·호감과 연결됨을 보였다. 2018년 3개국 연구에서는 **중국어 서체에서 효과가 없었다**. 한글로 일반화하는 것은 H.
- **#18 대소문자.** Xu, Chen & Liu(2017), Teng 외(2021). 한글에는 해당하지 않는다.
- **#19 손글씨.** Schroll 외(2018, JCR). 2차 보도만 확인(SO).
- **#20 유창성.** Song & Schwarz(2008): 읽기 어려운 서체가 과제를 어렵게 느끼게 한다(VE).
- **#21 명조/고딕.** 한글 서체 감성 연구는 2차 요약만 확인했다(SO).
- **#22, #23.** 수치 지침은 찾지 못했다(PC).

## 4. 레이아웃과 공간
- **#24 여백.** Pracejus, Olsen & O'Guinn(2006, JCR)은 여백의 의미에 대한 수사·역사 분석이다. Sevilla & Townsend(2016, JMR)는 실험·현장 연구로, 상품 주변 공간이 넓을수록 미적 매력과 프레스티지가 높아졌다. 한계: 리테일·광고 대상이다. **"여백이 넓다 → 고급"을 규칙으로 쓰지 않는다(post-mortem).**
- **#25 배치 편향.** Palmer, Gardner & Wickens(2008): 중앙 선호와 안쪽 편향.
- **#26 샷 스케일.** 영화 연구(Canini 외 2011, Benini 외 2022). 정지된 지면에 적용하는 것은 H.
- **#27 대칭.** Jacobsen & Höfel(2002): 추상 패턴에서 대칭이 '아름다움'의 가장 강한 예측자였다. 개인차가 있다.
- **첫인상.** Lindgaard 외(2006): 웹페이지의 시각적 매력은 50ms 노출로도 판단된다.

## 5. 복잡도·질서·곡률
- **#29.** Tuch 외(2012): 복잡도가 낮고 원형성이 높은 웹사이트가 가장 매력적이었다.
- **#30.** Berlyne의 역U 가설은 지지와 반증이 혼재한다.
- **#31.** Reber, Schwarz & Winkielman(2004): 반복·대칭·대비가 처리 유창성을 높이고, 유창성이 미적 쾌를 높인다.
- **#32.** Bar & Neta(2006): 곡선 선호.
- **#33 프랙털.** Taylor의 수치는 대중 기사 수준에서만 확인했다(SO).
- **측정 지표.** Rosenholtz 외(2007)의 Feature Congestion, Subband Entropy, Edge Density.

## 6. 물성
- **#34 종이 무게.** '무게 → 진지함'(Ackerman 외 2010)은 **사전등록 재현에서 재현되지 않았다**(Beek 외 2018).
- **#35 리소·망점·후가공.** PC.

## 7. 무드 모델
- **#36.** Russell(1980) 원형 모델, Mehrabian–Russell PAD(1974).
- **#37.** Kaplan(1995) 주의 회복 이론. '부드러운 매혹'의 조건이 불명확하다는 비판이 있다.

## 8. 모션
- **#38.** 이징에 대한 통제 연구는 찾지 못했다(PC). 느린 호흡(분당 10회 미만)의 이완 효과는 VE다(Zaccaro 외 2018 리뷰, 2023 메타분석). 화면의 리듬을 따라 호흡하게 된다는 것은 H.

## 9. 서사
- **#39.** 캡션 톤, 병치, 모티프는 PC다. 반복과 점화는 Reber 외(2004)로 VE이고, 텍스트 페르소나와 서체 페르소나의 상호작용은 Brumberger(2003)로 VE다.

## 출처 (검색 결과에서 직접 본 URL)
https://pubmed.ncbi.nlm.nih.gov/7996122/ · https://www.staff.uni-mainz.de/oberfeld/downloads/Wilms-Oberfeld2018_Article_ColorAndEmotionEffectsOfHueSat.pdf · https://pureportal.coventry.ac.uk/en/publications/a-study-of-colour-emotion-and-colour-preference-part-i-colour-emo/ · https://palmerlab.berkeley.edu/pdf/Schloss&Palmer(2011).pdf · https://pmc.ncbi.nlm.nih.gov/articles/PMC2889342 · https://scholarworks.unist.ac.kr/handle/201301/55113 · https://photographylife.com/how-light-creates-emotion-in-photography · https://petapixel.com/2017/02/23/orange-teal-look-popular-hollywood/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC3088122 · https://www.vr.tuwien.ac.at/publications/affective-image-classification-using-features-inspired-by-psychology-and-art-theory-2010/ · https://www.ingentaconnect.com/contentone/stc/tc/2003/00000050/00000002/art00008 · https://portfolio.erau.edu/en/publications/perception-of-fonts-perceived-personality-traits-and-uses/ · https://pure.royalholloway.ac.uk/en/publications/the-taste-of-typeface/ · https://link.springer.com/article/10.1007/s11002-016-9415-0 · https://ideas.repec.org/a/eee/jbrese/v136y2021icp164-175.html · https://news.umich.edu/if-its-hard-to-read-is-it-hard-to-do · https://koreascience.kr/article/CFKO200808349650644.pdf · https://ideas.repec.org/a/oup/jconrs/v33y2006i1p82-90.html · https://palmerlab.berkeley.edu/spatial.html · https://ieeexplore.ieee.org/document/8822965 · https://openhsu.ub.hsu-hh.de/entities/publication/14253 · https://research.google/pubs/pub38315/ · https://www.frontiersin.org/articles/10.3389/fnhum.2016.00536/full · https://bora.uib.no/bora-xmlui/bitstream/handle/1956/594/BORA_PSPR04.pdf?sequence=1 · https://nmr.mgh.harvard.edu/publications/journal_articles/743 · https://aeon.co/ideas/feel-good-fractals-from-ocean-waves-to-jackson-pollocks-art · https://dspace.mit.edu/handle/1721.1/37593 · https://pmc.ncbi.nlm.nih.gov/articles/PMC5839342/ · https://pdodds.w3.uvm.edu/research/papers/others/1980/russell1980a.pdf · https://psych.utah.edu/_resources/documents/psych4130/Kaplan_S.pdf · https://ricerca.unich.it/handle/11564/773399 · https://link.springer.com/article/10.1007/s12671-023-02294-2

## Round III — one rhetorical figure per spread (`edas/mood/rhetoric.py`)

| Spread | Figure | Device on the page | Anchor (verified) |
|---|---|---|---|
| NOCTURNE | 낯설게하기 (ostranenie) | Korean copy in 풀어쓰기 (syllables → jamo); mirrored title with a weight ramp of 100→900 across its letters; the normal sentence kept tiny as the key | Shklovsky, "Art as Technique" (1917): difficult form lengthens perception |
| LINEUP | 미장아빔 (mise en abyme) | the spread pasted into itself at 0.40ⁿ (fixed point, depth 6); the title ends in a 0.42ⁿ copy of itself; the "frame" sentence repeats inside itself | Gide, Journal (1893); Dällenbach, *Le récit spéculaire* (1977) |
| WILD | 데페이즈망 (dépaysement) | the amusement park hung upside down as the sky over the rock; the shop interior standing on lava; the night portrait framed in daylight; the word in a three-depth lattice after *Golconda* | Bianchi 2015 (Nougé/Magritte, "changement de décor"); Menil, *Magritte: The Mystery of the Ordinary*; Ruzzoli et al. 2020 (incongruous images and memory, not liking) |
| FABRIC | 아이러니 (irony) | MATCH. spelled with six mismatched faces on garment-colour chips; the measured ΔE00 values (12.2 / 19.9 / 42.2 / 48.3) labelled "MATCH ✓" | Burke, "perspective by incongruity"; there are few empirical studies on visual irony specifically |

Typography trends we could source from practitioner reports (2026): variable weight and width axes, kinetic stepping, and the revival of high-contrast serifs.
We found no sourced study for stretched or ransom-note type. These are conventions only.
The Lautréamont "chance meeting" line is not cited because its source was not verified.

## Final — round III refined (`edas/mood/final.py`, `examples/match_final.py`)

All four spreads now share one frame:
- 56 px margins.
- Running head at top left, figure index at top right, process line at bottom left, folio at bottom right.
- Inter Display weights 100–900 used as expression; Pretendard (OFL 1.1, `scripts/fetch_fonts.sh`) for Korean; JetBrains Mono for metadata.
- Process lines mix Mono and Pretendard on one baseline because the mono face has no Hangul.

Contemporary readings:
- **I:** out-of-square Hangul. Anchor: 안상수체, 1985, 탈네모꼴 (verified via press coverage). Also progressive blur.
- **II:** a fixed-point Droste recursion. The framed inset is re-mapped with the conformal spiral z ↦ z^β, β = 1 − i·ln(1/s)/2π, after Lenstra & de Smit's analysis of Escher's *Print Gallery*.
- **III:** cut-out collage with cast shadows; a Golconda lattice with depth-of-field blur.
- **IV:** ransom-note title, and a sentence set in seven Pretendard weights.

The user's approval to finalise is recorded in `output/match/final/final_spec.json`. The presentation PDF ends with a notes page that lists every photo operation and its limits: low-res source, unvalidated mood claims, practitioner trend sources.

## The one final spread: NOCTURNE, soft dandy (`edas/mood/contemporary.py`, `examples/match_final_dandy.py`)

The user directed this in four steps:
1. Round-I intensity is the right level ("이정도가 가장 적당해").
2. Bold, while following contemporary-art methods.
3. Change the mood to dandy.
4. Soft dandy ("부드러움 댄디").

NOCTURNE was rebuilt with three art methods (sources verified this session):
- **Divided, mirrored, repeated stripes** after Gerhard Richter (*Strip* works; *Patterns*, 2012). Here a column of the knit in the rock photo becomes the title's soft suiting stripe.
- **Maximal JPEG compression** after Thomas Ruff (*jpegs*, from 2002). Here it is the shadow print under each of the three places.
- **The poor image** after Hito Steyerl ("In Defense of the Poor Image", e-flux 2009). The real source size and enlargement are stated on the page.

The mood layer:
- Ivory paper with warm charcoal ink.
- Noto Serif KR (OFL) and Caladea Italic.
- A matte print (raised black point) with halation on the night photo.
- A softer slit-scan.

`nocturne_contemporary` is the same structure in a black, hard-edged version.
The mood is a design intention. No validated measurement backs it.

## WHERE PEOPLE STOP ? — rapport (`edas/mood/rapport.py`, `examples/stop_rapport.py`)

The user asked for this spread to be made too, with the mood "라포틱하게". We read that as rapport: a warm relationship of trust.

Tickle-Degnen & Rosenthal (1990) define rapport by three components: mutual attentiveness, positivity and coordination. They describe people interacting with each other, so mapping them onto a page is a design analogy and has not been tested:

| Component | On the page |
|---|---|
| Attentiveness | Each person inside the source's dashed box stays sharp. Everything outside the box gets horizontal motion blur. |
| Positivity | Warm light: cream paper, warm-brown ink, halation, a warm matte. The terracotta accent follows the hue of the source's labels, lightened to work on paper. |
| Coordination | The six person-centres sit evenly on one eye line, and the photos stand shoulder to shoulder at close distance (after Hall 1966, proxemics). |

The title is filled with stripes taken from the smoothie stall's light, divided, mirrored and repeated (after Richter).

Copy is verbatim. In the source, the body under (5.5) NEXT duplicates the body under (5.4) WHY?, so it is set once and the duplication was reported.
