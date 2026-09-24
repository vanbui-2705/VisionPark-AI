import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from app.alpr.onnx_provider import OnnxALPRRuntime
from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError

def test_onnx_provider_not_ready_without_weights():
    # Khởi tạo provider mà không có thư mục weights hợp lệ
    with patch("app.alpr.onnx_provider.os.path.exists", return_value=False):
        provider = OnnxALPRRuntime(weights_dir="/fake/weights/dir")
        
        # Test is_ready
        is_ready, msg = provider.is_ready()
        assert is_ready is False
        assert "Thiếu model" in msg
        
        # Test detect_and_read sẽ văng lỗi
        with pytest.raises(ALPRNotReadyError):
            provider.detect_and_read(b"fakebytes")

def test_onnx_provider_processing_error():
    provider = OnnxALPRRuntime(weights_dir="/fake/weights/dir")
    
    # Ép is_ready trả về True để bypass check
    with patch.object(provider, "is_ready", return_value=(True, "OK")):
        provider.detector_session = MagicMock()
        provider.ocr_session = MagicMock()
        
        # Gây lỗi khi cv2 decode
        with patch("app.alpr.utils.decode_image", side_effect=Exception("Decode failed")):
            with pytest.raises(ALPRProcessingError, match="Quá trình Inference bị lỗi: Decode failed"):
                provider.detect_and_read(b"fakebytes")
