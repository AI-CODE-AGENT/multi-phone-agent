"""
Worktree Coordinator Subagent (Subagent #16)
Orchestrates isolated Git worktrees (`D:/Project/multi-phone-agent-worktrees/<slug>`)
so that every specialist Subagent develops, tests, commits, and merges its feature or
self-improvement patch on a dedicated branch without main-branch conflicts.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.git_worktree_manager import GitWorktreeManager
from core.memory_manager import MemoryManager


class WorktreeCoordinatorSubagent:
    """Coordinates multi-agent Git worktree feature isolation, verification, and merge flows."""

    def __init__(
        self,
        worktree_mgr: Optional[GitWorktreeManager] = None,
        memory: Optional[MemoryManager] = None
    ):
        self.wt_mgr = worktree_mgr or GitWorktreeManager()
        self.memory = memory or MemoryManager()
        self.dispatch_history: List[Dict[str, Any]] = []

    def audit_worktree_topology(self) -> Dict[str, Any]:
        """Return all registered Git worktrees and their branch states."""
        worktrees = self.wt_mgr.list_worktrees()
        feature_wts = [w for w in worktrees if w.get("branch", "") != "main"]
        return {
            "status": "WORKTREE_TOPOLOGY_AUDITED",
            "repo_root": str(self.wt_mgr.repo_root),
            "worktrees_root": str(self.wt_mgr.worktrees_root),
            "total_worktrees": len(worktrees),
            "feature_worktrees_count": len(feature_wts),
            "worktrees": worktrees
        }

    def provision_subagent_worktree(
        self,
        feature_name: str,
        subagent_name: str,
        spec_markdown: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provision an isolated worktree for `subagent_name` and optionally write a
        feature spec doc inside `docs/worktree_features/<slug>.md` and commit it.
        """
        created = self.wt_mgr.create_feature_worktree(
            feature_name=feature_name,
            subagent_name=subagent_name
        )
        slug = created.get("feature_slug", self.wt_mgr.slugify_feature(feature_name))
        wt_path = Path(created["worktree_path"])

        commit_res = {"committed": False}
        if created.get("success") and spec_markdown:
            doc_dir = wt_path / "docs" / "worktree_features"
            doc_dir.mkdir(parents=True, exist_ok=True)
            doc_file = doc_dir / f"{slug}.md"
            doc_file.write_text(spec_markdown, encoding="utf-8")
            commit_res = self.wt_mgr.commit_in_worktree(
                worktree_path=wt_path,
                commit_message=f"feat({slug}): implement {slug} via {subagent_name}",
                subagent_name=subagent_name
            )

        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "feature_slug": slug,
            "subagent": subagent_name,
            "worktree_path": str(wt_path),
            "branch": created.get("branch"),
            "committed": commit_res.get("committed", False)
        }
        self.dispatch_history.append(record)
        return {
            "status": "WORKTREE_PROVISIONED" if created.get("success") else "ERROR",
            "worktree": created,
            "commit": commit_res
        }

    def merge_verified_worktree(
        self,
        feature_slug: str,
        push_remote: bool = False
    ) -> Dict[str, Any]:
        """Merge a verified feature worktree into `main`."""
        return self.wt_mgr.merge_worktree_to_main(
            feature_slug=feature_slug,
            push_remote=push_remote,
            cleanup_worktree=False
        )


if __name__ == "__main__":
    coord = WorktreeCoordinatorSubagent()
    print(coord.audit_worktree_topology())
