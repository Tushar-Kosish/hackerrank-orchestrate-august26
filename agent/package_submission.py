"""Create code.zip package containing runnable code, output, and chat transcript."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "code.zip"

def gather_paths():
    include = []
    # include agent code
    include.append(ROOT / "agent")
    # include dataset output if present
    if (ROOT / "dataset" / "output.csv").exists():
        include.append(ROOT / "dataset" / "output.csv")
    # include README and problem statement if present
    for name in ["README.md", "problem_statement (1).md", "problem_statement.md"]:
        p = ROOT / name
        if p.exists():
            include.append(p)
    # include onboarding/chat log if present
    log = ROOT / "hackerrank_log.txt"
    if log.exists():
        include.append(log)
    return include


def add_path(z, p: Path):
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            z.write(f, arcname=str(f.relative_to(ROOT)))
    else:
        z.write(p, arcname=str(p.relative_to(ROOT)))


def main():
    paths = gather_paths()
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            add_path(z, p)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
