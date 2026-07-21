import sys
from pathlib import Path

IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", "workspace", "build", "dist"}
FILE_EXTENSIONS = {".py", ".sh", ".md", ".yaml", ".yml"}

def clean_formatting(root_dir=".", fix=False):
    root = Path(root_dir)
    whitespace_only_lines = 0
    trailing_whitespace_lines = 0
    tab_indent_lines = 0
    modified_files = 0

    for path in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue

        if path.is_file() and path.suffix in FILE_EXTENSIONS:
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            lines = content.splitlines(keepends=True)
            new_lines = []
            file_changed = False

            for line_no, line in enumerate(lines, start=1):
                eol = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
                raw_line = line.rstrip("\r\n")

                # Case 1: Line is whitespace-only (tabs or spaces with no text)
                if raw_line and raw_line.strip() == "":
                    whitespace_only_lines += 1
                    print(f"🧹 [BLANK LINE WITH TABS/SPACES] {path}:{line_no}")
                    fixed_line = "" # Delete all tabs & spaces completely
                    file_changed = True

                # Case 2: Line has text, but contains trailing tabs or spaces
                elif raw_line != raw_line.rstrip(" \t"):
                    trailing_whitespace_lines += 1
                    print(f"⚠️  [TRAILING WHITESPACE] {path}:{line_no}")
                    # Strip trailing tabs/spaces, then convert any remaining leading tabs to 4 spaces
                    fixed_line = raw_line.rstrip(" \t").replace("\t", "    ")
                    file_changed = True

                # Case 3: Line has text, but uses tabs for indentation
                elif "\t" in raw_line:
                    tab_indent_lines += 1
                    print(f"❌ [TAB INDENTATION] {path}:{line_no}")
                    fixed_line = raw_line.replace("\t", "    ")
                    file_changed = True

                else:
                    fixed_line = raw_line

                new_lines.append(fixed_line + eol)

            if fix and file_changed:
                path.write_text("".join(new_lines), encoding="utf-8")
                modified_files += 1

    print("\n" + "=" * 60)
    print("📊 Formatting Audit Summary:")
    print(f"   - Blank lines with leftover tabs/spaces: {whitespace_only_lines}")
    print(f"   - Code lines with trailing whitespace:    {trailing_whitespace_lines}")
    print(f"   - Code lines with tab indentation:        {tab_indent_lines}")
    if fix:
        print(f"✅ Cleaned and fixed {modified_files} file(s).")
    print("=" * 60)

if __name__ == "__main__":
    auto_fix = "--fix" in sys.argv
    clean_formatting(".", fix=auto_fix)