"""V0 视觉观察的最小、确定性事件适配器。"""

from .events import VisionObservation, build_vision_event, confirm_observation
from .inference import observations_from_detections
from .pipeline import ingest_detections

__all__ = ["VisionObservation", "build_vision_event", "confirm_observation", "observations_from_detections", "ingest_detections"]
