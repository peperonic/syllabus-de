import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURE_PACK = ROOT / "tests" / "fixture" / "pack.yaml"


@pytest.fixture(scope="session")
def toy_dir(tmp_path_factory):
    """Build the toy knowledge base once, fully offline."""
    from builder.run import run
    d = tmp_path_factory.mktemp("toykb")
    results = run(pack_path=FIXTURE_PACK, data_dir=d)
    d.joinpath("build_results.txt").write_text(repr(results))
    return d


@pytest.fixture(scope="session")
def build_results(toy_dir):
    import ast
    return ast.literal_eval(toy_dir.joinpath("build_results.txt").read_text())


@pytest.fixture()
def api(toy_dir, tmp_path):
    from kb_api import KBApi
    return KBApi(pack_path=str(FIXTURE_PACK), data_dir=str(toy_dir), call_log=str(tmp_path / "calls.jsonl"))


@pytest.fixture()
def tampered_api(toy_dir, tmp_path):
    """A copy of the toy KB where structure-only text was stored by mistake.
    The API must still not return it."""
    import sqlite3
    from kb_api import KBApi
    d = tmp_path / "tampered"
    shutil.copytree(toy_dir, d)
    c = sqlite3.connect(d / "kb.sqlite")
    c.execute("UPDATE curriculum_node SET text = 'GEHEIMER VOLLTEXT KMK (eingeschleust)' "
              "WHERE document_id LIKE 'ZA:mathematik-kmk-%'")
    c.commit()
    c.close()
    return KBApi(pack_path=str(FIXTURE_PACK), data_dir=str(d))


def ctx(grade, date, land="ZA", school_form="Gymnasium", subject="Mathematik", **kw):
    return {"land": land, "school_form": school_form, "grade": grade, "subject": subject, "date": date, **kw}
