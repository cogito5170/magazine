"""Shared data for the PART 2 MATCH examples (coordinates in the supplied 2000x1231 image)."""
from edas.mood.photo_led import Photo

PHOTOS = [
    Photo("night", crop=(212, 39, 668, 997), outfit=(450, 599, 560, 799), person=(240, 329, 590, 997),
          label="night, riverside"),
    Photo("park", crop=(1120, 217, 2000, 639), outfit=(1730, 417, 1820, 597), person=(1680, 267, 1840, 639),
          label="dusk, amusement park"),
    Photo("shop", crop=(1113, 757, 1312, 1127), outfit=(1160, 882, 1220, 1032), person=(1130, 772, 1260, 1127),
          label="day, shop front"),
    Photo("rock", crop=(1370, 760, 1944, 1127), outfit=(1800, 860, 1910, 1030), person=(1600, 775, 1944, 1127),
          label="seaside, rocks"),
]
TEXTS = {
    "title": "MATCH.",
    "kicker": "FOUR PLACES, FOUR OUTFITS.",
    "body_ko": ["나는 그날 갈 장소에 옷의 톤을 맞춘다.", "장소가 틀이라면, 옷은 그 틀을 채우는 조합이다."],
    "running_head": "FROM THE INSIDE  —  PART 2 MATCH",
    "folio": "11",
}
