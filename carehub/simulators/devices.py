"""只产生标准化合成事件，绝不访问 BLE、MQTT、UART 或 GPIO。"""

from __future__ import annotations

from carehub.core.events import new_event


class DeviceSimulator:
    def event(self, device_id: str, sequence: int, event_type: str, *, quality: str = "HIGH") -> dict:
        privacy = "SENSITIVE" if event_type == "MEDICATION_DUE" else "INTERNAL"
        return new_event(
            aggregate=f"device:{device_id}", sequence=sequence, event_type=event_type,
            payload={"simulator": "G1", "device_id": device_id}, source="SIMULATOR", quality=quality, privacy=privacy,
        )

    def medication_due(self, task_id: str, sequence: int) -> dict:
        return new_event(
            aggregate=f"task:{task_id}", sequence=sequence, event_type="MEDICATION_DUE",
            payload={"simulator": "Dose", "evidence_state": "UNKNOWN"}, source="SIMULATOR", privacy="SENSITIVE",
        )
