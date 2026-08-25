from carehub.vision.events import VisionObservation
from carehub.vision.review import ReviewQueue


def test_low_confidence_candidate_requires_human_review():
    queue = ReviewQueue()
    item = queue.submit("review-1", VisionObservation("o-1", "fire", "MEDIUM", "CANDIDATE"), ["fire", "fire", "fire"])
    assert item.status == "PENDING"
    assert queue.decide("review-1", approved=True).status == "CONFIRMED"


def test_high_confidence_temporal_candidate_is_ready_but_not_business_state():
    queue = ReviewQueue()
    item = queue.submit("review-2", VisionObservation("o-2", "smoke", "HIGH", "CANDIDATE"), ["smoke", "smoke", "smoke"])
    assert item.status == "READY"
    assert queue.decide("review-2", approved=False).reason == "HUMAN_REJECTED"
