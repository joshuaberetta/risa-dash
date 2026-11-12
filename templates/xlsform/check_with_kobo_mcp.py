"""Check the template the way Kobo imports it, with kobo-mcp's own converter.

Run from a kobo-mcp checkout (formpack + pyxform 3.0, as KPI uses):

    cd ~/Desktop/work/repos/kobo-mcp
    uv run python -I /path/to/templates/xlsform/check_with_kobo_mcp.py \
        /path/to/templates/xlsform/RISA_template_<version>.xlsx [--odk-validate]

It runs convert_xlsform (formpack's xlsx_to_dicts, expand_content, replace_aliases),
kobo-mcp's pre-deploy checks, formpack's XForm build (what Kobo deploys) and pyxform on
the raw file (its warnings). --odk-validate also runs ODK Validate (needs Java).
Exit code 1 on any error or warning.
"""

import json
import sys
from pathlib import Path

# macOS can mark the venv's editable .pth file hidden, and Python then skips it; run from
# the kobo-mcp checkout so its src/ is found either way.
sys.path.insert(0, str(Path.cwd() / "src"))

from kobo_mcp.formcontent import xlsform  # noqa: E402
from kobo_mcp.formcontent.validate import validate
from kobo_mcp.formcontent.xform import to_xform
from pyxform.xls2xform import convert


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    path = Path(args[0])
    data = path.read_bytes()
    problems: list[str] = []

    sheets = xlsform.sheets_from_file(data)
    print("sheets:", ", ".join(sheets))
    content = xlsform.to_content(sheets)
    print(f"content: {len(content['survey'])} survey rows, {len(content['choices'])} choices, "
          f"translations {content.get('translations')}, translated {content.get('translated')}")
    problems += [f"validate: {e}" for e in validate(content)]

    result = to_xform(content)
    problems += [f"formpack: {w}" for w in result.warnings
                 if "last-saved" not in w]  # expected: carry-over defaults
    print(f"formpack XForm: {len(result.xml)} characters")

    warnings: list[str] = []
    odk = "--odk-validate" in sys.argv
    out = convert(str(path), warnings=warnings, validate=odk)
    problems += [f"pyxform: {w}" for w in warnings]
    print(f"pyxform XForm: {len(out.xform)} characters" + (" (ODK Validate passed)" if odk else ""))

    if "--dump" in sys.argv:
        Path("/tmp/risa_content.json").write_text(json.dumps(content, indent=1, ensure_ascii=False))
        Path("/tmp/risa_formpack.xml").write_text(result.xml)
        Path("/tmp/risa_pyxform.xml").write_text(out.xform)

    for p in problems:
        print("PROBLEM", p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
