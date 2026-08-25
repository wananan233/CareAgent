"""跌倒候选的时序确认与人工复核入口。"""
from .fall import FallCandidate
from .inference import observations_from_detections
from .review import ReviewItem, ReviewQueue

def submit_fall_candidate_for_review(queue: ReviewQueue, candidate: FallCandidate, *, review_id: str, observation_id: str, history: list[str]) -> ReviewItem:
    """将单帧候选交给连续帧规则和人工复核队列。"""
    observation = observations_from_detections(({"observation_id": observation_id, "label": candidate.label, "confidence": candidate.confidence},))[0]
    return queue.submit(review_id, observation, history)
