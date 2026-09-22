from abc import ABC, abstractmethod


class ImageStorage(ABC):
    """Cổng (Port) để lưu trữ ảnh thô thu thập được trong quá trình nhận diện."""

    @abstractmethod
    def save_image(self, image_bytes: bytes, lane_id: str) -> str:
        """
        Lưu ảnh và trả về mã/khóa truy xuất.
        Tham số:
            image_bytes: Dữ liệu ảnh thô định dạng JPEG/PNG.
            lane_id: ID của làn xe nơi bức ảnh được chụp.
        Trả về:
            Chuỗi (String) đại diện cho storage key hoặc object ID của ảnh.
        """
        pass

    @abstractmethod
    def delete_image(self, image_key: str, lane_id: str) -> None:
        """Remove an image after persistence fails."""
        raise NotImplementedError
