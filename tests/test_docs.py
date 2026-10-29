"""The README's pictures: every image it names exists, and the hero matches its script."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/Misoto22/tc002/main/"


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_readme_image_is_in_the_repository():
    readme = (ROOT / "README.md").read_text()
    paths = re.findall(rf'(?:src|srcset)="{re.escape(RAW)}([^"]+)"', readme)
    paths += re.findall(rf"\]\({re.escape(RAW)}([^)]+\.(?:png|gif|svg))\)", readme)
    assert len(paths) > 20
    missing = [p for p in paths if not (ROOT / p).is_file()]
    assert not missing, f"README names images that are not committed: {missing}"


def test_gallery_images_share_one_width_so_rows_line_up():
    readme = (ROOT / "README.md").read_text()
    widths = set(re.findall(r'docs/screens/[\w-]+\.gif" width="(\d+)"', readme))
    assert widths == {"192"}


def test_hero_banner_is_what_its_script_draws():
    hero = _script("render_hero")
    for theme in ("light", "dark"):
        assert (ROOT / "docs" / f"hero-{theme}.svg").read_text() == hero.svg(theme), (
            f"docs/hero-{theme}.svg is stale: run scripts/render_hero.py"
        )
