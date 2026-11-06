"""Scanner regression cases contain invented strings, never actual credentials."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "public_check", Path(__file__).resolve().parents[1] / "scripts/check_public_release.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


@pytest.mark.parametrize(
    "name,body",
    [
        ("example.dta", "invented"),
        ("report.private.json", "{}"),
        ("unreviewed.csv", "a,b"),
        ("example.md", "/" + "Users" + "/INVENTED/example"),
        ("example.md", "ghp_" + "A" * 36),
        ("example.svg", "<svg><script>invented</script></svg>"),
        ("example.svg", '<svg><image href="https://example.invalid/invented.png"/></svg>'),
    ],
)
def test_artifact_rejection(tmp_path, name, body):
    (tmp_path / name).write_text(body)
    with pytest.raises(ValueError):
        CHECK.check_file(tmp_path, name)


def test_safe_synthetic_svg_and_relative_link(tmp_path):
    p = tmp_path / "SYNTHETIC.svg"
    p.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>INVENTED ONLY</text></svg>')
    CHECK.check_file(tmp_path, p.name)
    assert CHECK.check_links(tmp_path, tmp_path / "readme.md", "[example](SYNTHETIC.svg)") == 1
    with pytest.raises(ValueError):
        CHECK.check_links(tmp_path, tmp_path / "readme.md", "[missing](missing.svg)")


def test_symlink_refused(tmp_path):
    (tmp_path / "invented.md").write_text("invented")
    (tmp_path / "link.md").symlink_to(tmp_path / "invented.md")
    with pytest.raises(ValueError):
        CHECK.check_file(tmp_path, "link.md")
