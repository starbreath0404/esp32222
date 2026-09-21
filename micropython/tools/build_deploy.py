"""Build upload-ready single-, left- and right-glove directories."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def copy_tree_files(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.py"):
        shutil.copy2(path, destination / path.name)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    for role in ("left_glove", "right_glove"):
        destination = DIST / ("left" if role == "left_glove" else "right")
        copy_tree_files(ROOT / "common", destination)
        copy_tree_files(ROOT / role, destination)
    single = DIST / "single"
    copy_tree_files(ROOT / "common", single)
    for filename in ("audio.py", "serial_control.py"):
        shutil.copy2(ROOT / "right_glove" / filename, single / filename)
    copy_tree_files(ROOT / "single_glove", single)
    print("Built:", DIST)


if __name__ == "__main__":
    main()
