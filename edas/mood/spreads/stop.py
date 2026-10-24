"""Measured layout of the user's 'WHERE PEOPLE STOP ?' spread (1206×677 JPEG).

Cells are 218×194 px.  The person boxes are the dashed boxes drawn in the source, in cell-local px, read
from a 3× gridded enlargement.  Copy is transcribed verbatim.  In the source the body under (5.5) NEXT is
the same text as under (5.4) WHY?; it is kept once here and the duplication is reported.
"""
CELLS = {  # key: (cell x, cell y, person box x0, y0, x1, y1)
    "01": (276, 43, 89, 100, 129, 133),
    "02": (712, 43, 70, 102, 116, 143),
    "03": (58, 237, 77, 53, 141, 168),
    "04": (494, 237, 49, 3, 163, 178),
    "05": (930, 237, 58, 107, 159, 191),
    "06": (712, 430, 67, 62, 124, 190),
}
CELL_W, CELL_H, LABEL_CROP = 218, 194, 22      # the top 22 px carry the baked '(0n)' label

TEXTS = {
    "n51": "(5.1)", "title": "WHERE PEOPLE STOP ?",
    "n52": "(5.2)", "void": "01-03 VOID",
    "n53": "(5.3)", "sense": "04-06 SENSE",
    "n54": "(5.4)", "why": "WHY?",
    "n55": "(5.5)", "next": "NEXT",
    "body": "그들을 멈추게 한 것은 여백이었다. 얕은 물, 파라솔 옆 의자, 가게 앞 계단은 잠시 머무를 수 있는 공간을 "
            "제공한다. 불판 앞 연기와 간판의 빛, 메뉴판의 사진들은 감각을 자극해 멈출 이유를 제공하였다. "
            "사람은 머물 수 있어야 들여다보고, 들여다봐야 고른다.",
}
