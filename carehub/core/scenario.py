"""C3 固定、可复现的模拟场景；不访问真实设备或外部服务。"""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .service import CareCore
from carehub.simulators.devices import DeviceSimulator


@dataclass(frozen=True)
class ScenarioRun:
    scenario_run_id: str
    seed: int
    fixed_time: str
    emitted_event_ids: tuple[str, ...]


class ScenarioService:
    def __init__(self, core: CareCore, *, fixed_time: datetime | None = None,
                 publish_view: Callable[..., int] | None = None) -> None:
        self.core, self.fixed_time, self.publish_view = core, fixed_time or datetime(2026, 8, 22, tzinfo=timezone.utc), publish_view

    def run(self, *, scenario: str, seed: int, tenant_id: str, household_id: str, subject_id: str) -> ScenarioRun:
        if scenario not in {"DOSE", "SAFETY"}: raise ValueError("未知模拟场景")
        random.Random(seed)  # 明确 seed 是场景可复现输入，未来分支不得使用全局随机源。
        simulator = DeviceSimulator(tenant_id=tenant_id, household_id=household_id, subject_id=subject_id)
        event = simulator.medication_due("morning", 1) if scenario == "DOSE" else simulator.event("sos", 1, "SOS_PRESSED")
        event["event_id"] = f"scenario-{scenario.lower()}-{seed}-{event['event_id']}"
        self.core.ingest(event)
        if self.publish_view:
            for view in ("tasks", "timeline") if scenario == "DOSE" else ("alerts", "timeline"):
                self.publish_view(tenant_id=tenant_id, household_id=household_id, subject_id=subject_id, view=view)
        return ScenarioRun(f"scenario-{uuid.uuid4()}", seed, self.fixed_time.isoformat(), (event["event_id"],))
