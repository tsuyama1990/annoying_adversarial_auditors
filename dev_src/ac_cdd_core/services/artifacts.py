from pathlib import Path

from ..config import settings
from ..domain_models import CyclePlan
from ..utils import logger


class ArtifactManager:
    """
    Manages cycle artifacts (SPEC, UAT, etc.).
    """

    def save_plan_artifacts(self, cycle_id: str, plan: CyclePlan) -> None:
        """
        Saves the CyclePlan artifacts to the cycle directory.
        """
        cycle_dir = Path(settings.paths.templates) / f"CYCLE{cycle_id}"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        # Save artifacts
        for artifact in [plan.spec_file, plan.schema_file, plan.uat_file]:
            p = Path(artifact.path)
            target_path = cycle_dir / p.name
            target_path.write_text(artifact.content, encoding="utf-8")
            logger.info(f"Saved {target_path}")

        # Save thought process
        (cycle_dir / "PLAN_THOUGHTS.md").write_text(plan.thought_process, encoding="utf-8")
