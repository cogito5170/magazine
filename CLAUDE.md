# EDAS — editorial design analysis + mood spreads

- **Magazine / mood work — automatic**: whenever the user supplies photos, a page image, slides or a PDF and asks for a magazine page, a mood or feeling, "알아서", or a sellable / print-ready edition, load and follow the `magazine` skill (`.claude/skills/magazine/SKILL.md`) without waiting for a slash command.
  - If no mood is given, read each page's atmosphere and choose one, using `edas mood read` and `docs/mood_library.md`.
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
