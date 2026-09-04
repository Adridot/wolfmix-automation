"""Repository boundaries: missing declarations and broken links fail without a corpus."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check
import wpj_links


class RepositoryGuards(unittest.TestCase):
    def test_public_annotations_include_methods_and_keyword_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "README.md").write_text("# Home\nReader: developer. Question: how?\n")
            module = root / "tools" / "example.py"
            module.write_text('''"""Role. Module group: Format. Reference: SPEC.md."""
def good(value: bytes, *, limit: int = 1) -> bytes:
    return value[:limit]
def _private(value):
    return value
def broken(value: int, *, flag=False):
    return value
class Example:
    def __init__(self, name):
        self.name = name
    def method(self, *values, **options) -> None:
        pass
''')
            errors = check.architecture_errors(root)
            self.assertEqual(len(errors), 3, errors)
            self.assertTrue(any("broken lacks annotations: flag, return" in e for e in errors))
            self.assertTrue(any("__init__ lacks annotations: name, return" in e for e in errors))
            self.assertTrue(any("method lacks annotations: values, options" in e for e in errors))

    def test_new_page_needs_reader_question_and_direct_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            readme = root / "README.md"
            readme.write_text("# Home\nReader: users. Question: where?\n")
            page = root / "docs" / "guide.md"
            page.write_text("# Guide\n")
            self.assertEqual(len(check.architecture_errors(root)), 2)
            page.write_text("# Guide\nReader: users. Question: how?\n")
            self.assertEqual(len(check.architecture_errors(root)), 1)
            readme.write_text(readme.read_text() + "[Guide](docs/guide.md)\n")
            self.assertEqual(check.architecture_errors(root), [])

    def test_independent_oracle_cannot_import_shared_reader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "README.md").write_text("# Home\nReader: users. Question: where?\n")
            (root / "tools" / "wpj_inspect.py").write_text(
                '"""Independent oracle. Module group: Format."""\nfrom wpj_wire import fields\n')
            self.assertTrue(any("oracle imports" in e for e in check.architecture_errors(root)))

    def test_module_role_and_group_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "README.md").write_text("# Home\nReader: users. Question: where?\n")
            (root / "tools" / "example.py").write_text("value = 1\n")
            self.assertEqual(len(check.architecture_errors(root)), 2)

    def test_child_checks_use_the_selected_python(self) -> None:
        with patch.object(check.subprocess, "run") as run:
            run.return_value.stdout = ""
            run.return_value.returncode = 0
            check.executer(["python3", "tools/wpjlib.py"])
            self.assertEqual(run.call_args.args[0], [check.sys.executable, "tools/wpjlib.py"])


class SectionLinks(unittest.TestCase):
    def test_heading_markup_duplicates_explicit_anchors_and_fences(self) -> None:
        text = '''# Café `some_name.py` — **wire**
## Same
## Same
## Same-1
<a id="stable"></a>
<a name="old"></a>
````md
# Hidden
```
# Still hidden
````
Setext title
============
'''
        self.assertEqual(wpj_links.anchors(text), {
            "café-some_namepy--wire", "same", "same-1", "same-1-1",
            "stable", "old", "setext-title",
        })

    def test_broken_section_fails_even_when_the_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "index.md"
            target = root / "guide.md"
            target.write_text('# Good\n<a id="stable"></a>\n')
            source.write_text(
                "# Home\n[local](#home)\n[ok](guide.md#good)\n"
                "[stable](guide.md#stable)\n[missing](guide.md#gone)\n"
                "[missing local](#absent)\n")
            tracked = [str(source), str(target)]
            self.assertEqual(wpj_links.casses([source], tracked), [
                (source, 5, "guide.md#gone"), (source, 6, "#absent"),
            ])
            target.write_text("# Renamed\n")
            self.assertEqual(len(wpj_links.casses([source], tracked)), 4)

    def test_url_escaped_names_and_untracked_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "index.md"
            target = root / "two words.md"
            target.write_text("# Café\n")
            source.write_text("[ok](two%20words.md#caf%C3%A9)\n")
            self.assertEqual(wpj_links.casses([source], [str(source), str(target)]), [])
            self.assertEqual(len(wpj_links.casses([source], [str(source)])), 1)
