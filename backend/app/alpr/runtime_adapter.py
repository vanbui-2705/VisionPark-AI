import time
import random
from .schema import ALPRResult, BoundingBox

class FakeALPRRuntime:
    def __init__(self):
        self.version = "v1.0-fake"
        
    def detect_and_read(self, image_matrix) -> ALPRResult:
        start_time = time.time()
        time.sleep(random.uniform(0.2, 0.5))
        latency_ms = int((time.time() - start_time) * 1000)

        if random.random() < 0.05:
            raise TimeoutError("Model timeout hoặc quá tải")

        # Trả về đối tượng ALPRResult của Người 1
        return ALPRResult(
            plate_number="29A-123.45",
            bbox=BoundingBox(x1=100, y1=200, x2=400, y2=300),
            confidence=0.98,
            processing_time_ms=latency_ms,
            requires_confirmation=False
        )

ai_runtime = FakeALPRRuntime()