# EDAS — editorial design analysis + mood spreads

- **Mood work**: when the user gives an image and a feeling ("이 느낌으로 만들어줘"), follow `.claude/skills/mood/SKILL.md` exactly (`/mood`).
- **Approved results reproduce pixel-for-pixel**:
  - `edas mood list`
  - `edas mood render <name> --image sources/<file>` must report "identical to the approved file".
  - Never change the functions behind them. Add new ones instead.
- **Rules**
  - Never modify originals.
  - Never generate or inpaint photo content.
  - Keep copy verbatim.
  - Only numbers that were measured.
  - Only sources that were actually checked.
  - Aesthetic and mood claims are hypotheses.
  - See also `docs/postmortems/vmd-redesign-failure.md`.
- **Tests**: `python3 -m unittest discover -s tests -t .`
- **Fonts** (OFL): `edas mood fonts --install` installs Pretendard and Noto Serif KR into `~/.local/share/fonts`.
- **Language**: reply to the user in Korean.
