"""
Subagent Worktree Orchestrator Script
Demonstrates & executes parallel feature development where each Subagent works
in its own isolated Git worktree (`D:/Project/multi-phone-agent-worktrees/<slug>`),
commits atomically to its feature branch (`feat/<slug>`), and merges/pushes to GitHub `multi-phone-agent`.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.code_improver_subagent import CodeImproverSubagent


def run_worktree_feature_pipeline():
    improver = CodeImproverSubagent()
    wm = improver.worktree_mgr

    features = [
        (
            "real-phone-farm",
            "RealDeviceScoutSubagent",
            "docs/worktree_features/real_phone_farm.md",
            "# Feature Worktree: Optional Real Phone Farm & Wireless ADB\n\n"
            "- **Subagent Owner**: `RealDeviceScoutSubagent`\n"
            "- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/real-phone-farm`\n"
            "- **Branch**: `feat/real-phone-farm`\n"
            "- **Capabilities**: Hybrid/Real/AVD mode switching, Wireless TCP/IP :5555 auto-provisioning, Battery & Thermal Guard.\n",
            "feat(real-phone-farm): isolate RealDeviceScoutSubagent feature worktree and documentation"
        ),
        (
            "group-broadcast-sync",
            "GroupSyncSubagent",
            "docs/worktree_features/group_broadcast_sync.md",
            "# Feature Worktree: Synchronized Multi-Phone Group Broadcast\n\n"
            "- **Subagent Owner**: `GroupSyncSubagent`\n"
            "- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/group-broadcast-sync`\n"
            "- **Branch**: `feat/group-broadcast-sync`\n"
            "- **Capabilities**: Normalized cross-resolution tap/swipe scaling across 720x1600, 1080x2400, and 1440x3200 devices.\n",
            "feat(group-broadcast-sync): isolate GroupSyncSubagent multi-device broadcast feature worktree"
        ),
        (
            "experience-miner-macros",
            "ExperienceMinerSubagent",
            "docs/worktree_features/experience_miner_macros.md",
            "# Feature Worktree: Mobile-Agent-E Trajectory Experience Miner\n\n"
            "- **Subagent Owner**: `ExperienceMinerSubagent`\n"
            "- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/experience-miner-macros`\n"
            "- **Branch**: `feat/experience-miner-macros`\n"
            "- **Capabilities**: Distills healed trajectories into reusable normalized Macro-Action shortcuts.\n",
            "feat(experience-miner-macros): isolate ExperienceMinerSubagent macro shortcut worktree"
        ),
        (
            "self-evolution-loop",
            "SelfEvolutionEngine",
            "docs/worktree_features/self_evolution_loop.md",
            "# Feature Worktree: 12-Subagent Autonomous Self-Evolution Loop\n\n"
            "- **Subagent Owner**: `SelfEvolutionEngine`\n"
            "- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/self-evolution-loop`\n"
            "- **Branch**: `feat/self-evolution-loop`\n"
            "- **Capabilities**: Autonomous Backlog Ideation -> Plan -> Group Sync -> Execute -> Heal -> Patch -> Regression -> Prompt Evolution.\n",
            "feat(self-evolution-loop): isolate SelfEvolutionEngine 12-subagent loop worktree"
        ),
    ]

    results = []
    for slug, agent, rel_path, content, msg in features:
        res = improver.develop_feature_in_worktree(slug, agent, rel_path, content, msg)
        print(f"[{agent}] Worktree '{res['branch']}' at {res['worktree_path']} -> Committed: {res['commit']['committed']}")
        m_res = wm.merge_worktree_to_main(slug, push_remote=True, cleanup_worktree=False)
        print(f" -> Merged '{slug}' into main & pushed to origin: {m_res['success']}")
        results.append({"worktree": res, "merge": m_res})
    return results


if __name__ == "__main__":
    run_worktree_feature_pipeline()
