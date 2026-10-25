"""Composers for mood specs that carry their own structure block, one module per structure kind.

Interface: render(crops, texts, layer, persons, H) -> (page, spec) where spec has text_boxes, photo_boxes and
texts_set (the exact strings set).  Written by the mood writer; judged by edas/mood/judge.py.
"""
