from __future__ import annotations

import subprocess


def run_git(repo_path: str, *args: str) -> str:
    cmd = ["git"]
    if repo_path != "":
        cmd.extend(["-C", repo_path])
    cmd.extend(args)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: exit={proc.returncode}: {output.strip()}"
        )
    return output.strip()
