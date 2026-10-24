import functools
import os
import tempfile

from edas.config import load_config

TMP = tempfile.mkdtemp(prefix="edas-tests-")


@functools.lru_cache(maxsize=None)
def synthetic():
    from edas.synth import make_test_pdf
    path = os.path.join(TMP, "synthetic.pdf")
    truth = make_test_pdf(path, pages=4)
    return path, truth


@functools.lru_cache(maxsize=None)
def bilingual():
    from edas.synth import make_bilingual_pdf
    path = os.path.join(TMP, "bilingual.pdf")
    truth = make_bilingual_pdf(path)
    return path, truth


@functools.lru_cache(maxsize=None)
def analysed(name="synthetic"):
    from edas.pipeline import RunOptions, analyze
    path = synthetic()[0] if name == "synthetic" else bilingual()[0]
    return analyze(path, load_config(), RunOptions(with_candidates=False))
