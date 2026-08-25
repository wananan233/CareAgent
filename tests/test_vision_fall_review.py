from carehub.vision.fall import FallCandidate
from carehub.vision.fall_review import submit_fall_candidate_for_review
from carehub.vision.review import ReviewQueue

def test_fall_candidate_requires_temporal_confirmation_and_review():
    item = submit_fall_candidate_for_review(ReviewQueue(), FallCandidate("fall_candidate", .9, "sha256:x"), review_id="r1", observation_id="o1", history=["fall_candidate"])
    assert item.status == "PENDING"
    assert item.reason == "LOW_CONFIDENCE_OR_UNCONFIRMED"
