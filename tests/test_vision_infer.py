from types import SimpleNamespace

from carehub.vision.infer import YOLOInferenceService


def test_inference_service_returns_bounded_detection_metadata():
    boxes = SimpleNamespace(conf=SimpleNamespace(tolist=lambda: [0.9]), xyxy=SimpleNamespace(__getitem__=lambda self, index: SimpleNamespace(tolist=lambda: [1, 2, 3, 4])), cls=SimpleNamespace(__getitem__=lambda self, index: SimpleNamespace(item=lambda: 0)))
    class Values:
        def __init__(self, values): self.values = values
        def tolist(self): return self.values
        def __getitem__(self, index): return Values(self.values[index])
        def item(self): return self.values
    boxes = SimpleNamespace(conf=Values([0.9]), xyxy=Values([[1, 2, 3, 4]]), cls=Values([0]))
    predictor = SimpleNamespace(predict=lambda **kwargs: [SimpleNamespace(boxes=boxes, names={0: "fire"})])
    result = YOLOInferenceService(predictor, model_version="sha256:test").infer(object(), frame_timestamp="2026-08-25T20:00:00+00:00")
    assert result[0].label == "fire"
    assert result[0].bbox_xyxy == (1.0, 2.0, 3.0, 4.0)
    assert result[0].model_version == "sha256:test"
