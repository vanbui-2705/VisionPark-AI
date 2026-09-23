class ALPRError(Exception):
    """Lớp cơ sở cho các exception của ALPR."""

    pass


class ALPRNotReadyError(ALPRError):
    """Lỗi văng ra khi model ONNX chưa được tải hoặc thiếu file trọng số (weights)."""

    def __init__(self, message="Runtime ALPR chưa sẵn sàng hoặc bị thiếu file trọng số."):
        super().__init__(message)


class ALPRProcessingError(ALPRError):
    """Lỗi văng ra khi gặp sự cố trong quá trình Inference (VD: lỗi OpenCV, lỗi phiên chạy ONNX)."""

    def __init__(self, message="Đã xảy ra lỗi trong quá trình chạy Inference ALPR."):
        super().__init__(message)
