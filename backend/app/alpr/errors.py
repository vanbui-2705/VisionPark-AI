class ALPRError(Exception):
    """Lớp cơ sở cho các exception của ALPR."""

    pass


class ALPRInvalidImageError(ALPRError):
    """Raised when an input image is empty, unsupported, too large, or corrupt."""

    def __init__(self, message="Input image is invalid."):
        super().__init__(message)


class ALPRNotReadyError(ALPRError):
    """Lỗi văng ra khi model ONNX chưa được tải hoặc thiếu file trọng số (weights)."""

    def __init__(self, message="Runtime ALPR chưa sẵn sàng hoặc bị thiếu file trọng số."):
        super().__init__(message)


class ALPRModelMissingError(ALPRNotReadyError):
    """Raised when the configured model manifest or weight is missing."""


class ALPRManifestError(ALPRNotReadyError):
    """Raised when the model manifest cannot be read or is incomplete."""


class ALPRChecksumMismatchError(ALPRNotReadyError):
    """Raised when model bytes do not match the manifest checksum."""


class ALPRDependencyError(ALPRNotReadyError):
    """Raised when an optional detector/OCR dependency is unavailable."""


class ALPRModelLoadError(ALPRNotReadyError):
    """Raised when the model dependency cannot load the configured artifact."""


class ALPRProcessingError(ALPRError):
    """Lỗi văng ra khi gặp sự cố trong quá trình Inference (VD: lỗi OpenCV, lỗi phiên chạy ONNX)."""

    def __init__(self, message="Đã xảy ra lỗi trong quá trình chạy Inference ALPR."):
        super().__init__(message)


class ALPRInferenceError(ALPRProcessingError):
    """Raised when the detector fails while processing an image."""


class ALPROCRTimeoutError(ALPRInferenceError):
    """Raised when OCR exceeds the provider timeout."""
