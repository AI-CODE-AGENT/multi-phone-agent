"""
Git Worktree Subagent Manager (AMAF 3.0)
Enables each specialist Subagent to isolate feature development, code patches,
and self-improvements inside dedicated Git worktrees (`D:/Project/multi-phone-agent-worktrees/<feature-slug>`)
on dedicated branches (`feat/<feature-slug>`), run automated verification, commit atomically,
and push/merge cleanly back into `main`.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKTREES_ROOT = PROJECT_ROOT.parent / f"{PROJECT_ROOT.name}-worktrees"


class GitWorktreeManager:
    """Manages isolated Git worktrees for parallel Multi-Agent feature engineering."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        worktrees_root: Optional[Path] = None
    ):
        self.repo_root = Path(repo_root or PROJECT_ROOT).resolve()
        self.worktrees_root = Path(worktrees_root or DEFAULT_WORKTREES_ROOT).resolve()
        self.worktrees_root.mkdir(parents=True, exist_ok=True)

    def _run_git(self, args: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> Tuple[int, str, str]:
        target_cwd = str(cwd or self.repo_root)
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=target_cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return -1, "", str(e)

    @staticmethod
    def slugify_feature(feature_name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", feature_name.strip().lower()).strip("-")
        return clean or f"feature-{int(time.time())}"

    def create_feature_worktree(
        self,
        feature_name: str,
        subagent_name: str = "CodeImproverSubagent",
        base_branch: str = "main",
        branch_prefix: str = "feat"
    ) -> Dict[str, Any]:
        """
        Create an isolated Git worktree at `../multi-phone-agent-worktrees/<slug>`
        on branch `<branch_prefix>/<slug>`.
        """
        slug = self.slugify_feature(feature_name)
        branch_name = f"{branch_prefix}/{slug}"
        wt_path = self.worktrees_root / slug

        # If worktree already exists, return its info
        if wt_path.exists() and (wt_path / ".git").exists():
            return {
                "success": True,
                "status": "EXISTING_WORKTREE",
                "subagent": subagent_name,
                "feature_slug": slug,
                "branch": branch_name,
                "worktree_path": str(wt_path)
            }

        # Prune stale worktree entries first
        self._run_git(["worktree", "prune"])

        # Check if branch already exists
        code_br, out_br, _ = self._run_git(["branch", "--list", branch_name])
        if out_br.strip():
            code, out, err = self._run_git(["worktree", "add", str(wt_path), branch_name])
        else:
            code, out, err = self._run_git(["worktree", "add", "--no-track", "-b", branch_name, str(wt_path), base_branch])

        ok = code == 0 and wt_path.exists()
        return {
            "success": ok,
            "status": "CREATED" if ok else "ERROR",
            "subagent": subagent_name,
            "feature_slug": slug,
            "branch": branch_name,
            "worktree_path": str(wt_path),
            "message": out if ok else (err or out)
        }

    def list_worktrees(self) -> List[Dict[str, str]]:
        """List all active Git worktrees registered to this repository."""
        code, out, _ = self._run_git(["worktree", "list", "--porcelain"])
        if code != 0 or not out:
            return []

        worktrees = []
        current: Dict[str, str] = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
                continue
            if line.startswith("worktree "):
                current["path"] = line.split(" ", 1)[1].strip()
            elif line.startswith("HEAD "):
                current["head"] = line.split(" ", 1)[1].strip()
            elif line.startswith("branch "):
                current["branch"] = line.split(" ", 1)[1].strip().replace("refs/heads/", "")
        if current:
            worktrees.append(current)
        return worktrees

    def commit_in_worktree(
        self,
        worktree_path: Path,
        commit_message: str,
        subagent_name: str = "Subagent"
    ) -> Dict[str, Any]:
        """Stage all changes in a feature worktree and create a conventional commit."""
        wt = Path(worktree_path)
        self._run_git(["add", "-A"], cwd=wt)
        code_st, status_out, _ = self._run_git(["status", "--porcelain"], cwd=wt)
        if not status_out.strip():
            return {"success": True, "committed": False, "message": "Working tree clean, nothing to commit."}

        code, out, err = self._run_git(
            ["commit", "-m", commit_message, "-m", f"Automated-By: {subagent_name}"],
            cwd=wt
        )
        return {
            "success": code == 0,
            "committed": code == 0,
            "worktree_path": str(wt),
            "commit_message": commit_message,
            "output": out or err
        }

    def merge_worktree_to_main(
        self,
        feature_slug: str,
        branch_prefix: str = "feat",
        push_remote: bool = True,
        cleanup_worktree: bool = False
    ) -> Dict[str, Any]:
        """Merge a verified feature worktree branch into `main` and optionally push to origin."""
        slug = self.slugify_feature(feature_slug)
        branch_name = f"{branch_prefix}/{slug}"
        wt_path = self.worktrees_root / slug

        # Merge into main with --no-ff
        code_m, out_m, err_m = self._run_git(["merge", "--no-ff", branch_name, "-m", f"Merge branch '{branch_name}' into main"])
        merged = code_m == 0

        push_msg = ""
        if merged and push_remote:
            _, out_p, err_p = self._run_git(["push", "origin", "main", branch_name])
            push_msg = out_p or err_p

        if merged and cleanup_worktree and wt_path.exists():
            self._run_git(["worktree", "remove", "--force", str(wt_path)])

        return {
            "success": merged,
            "branch": branch_name,
            "merge_output": out_m or err_m,
            "push_output": push_msg
        }


if __name__ == "__main__":
    mgr = GitWorktreeManager()
    print("Repo Root:", mgr.repo_root)
    print("Worktrees Root:", mgr.worktrees_root)
    print("Active Worktrees:", mgr.list_worktrees())
