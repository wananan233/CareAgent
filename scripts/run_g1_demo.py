"""运行 G1 合成闭环并输出可审查状态。"""

from pathlib import Path

from carehub.core.service import CareCore
from carehub.simulators.devices import DeviceSimulator


database = Path("var/g1-demo.db")
database.parent.mkdir(exist_ok=True)
if database.exists():
    database.unlink()
core = CareCore(database)
simulator = DeviceSimulator()
for event in [
    simulator.medication_due("synthetic-morning", 1),
    simulator.event("safe-01", 1, "SMOKE_DETECTED"),
    simulator.event("careport-01", 1, "SOS_PRESSED"),
    simulator.event("radar-01", 1, "INACTIVITY_DETECTED"),
]:
    core.ingest(event)
print({"journal_mode": core.store.journal_mode(), "outbox_pending": core.store.pending_outbox_count(), "alerts": core.projections.alerts, "tasks": core.projections.tasks, "projection_hash": core.projections.digest()})
core.close()
