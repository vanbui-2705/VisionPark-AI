"""Concrete implementation of DetectionRecorder port."""
from sqlalchemy.orm import Session
from sqlalchemy import insert
from typing import Optional

from app.alpr.schema import ALPRResult
from app.alpr.ports.detection_recorder import DetectionRecorder


class DatabaseDetectionRecorder(DetectionRecorder):
    """
    Implementation lưu kết quả nhận diện xuống database.
    """
    
    def record_detection(self, lane_id: str, image_key: str, result: ALPRResult) -> str:
        """
        Lưu detection record vào bảng detections.
        
        Args:
            lane_id: ID của làn xe
            image_key: Storage key của ảnh đã lưu
            result: Kết quả ALPR từ model
            
        Returns:
            ID của bản ghi mới được tạo
        """
        from app.database.session import SessionLocal
        from app.database.models import Detection
        
        with SessionLocal() as db:
            # Chuẩn bị dữ liệu
            plate_data = {
                "raw": result.plate_number,
                "normalized": None,
            }
            if result.plate_number:
                plate_data["normalized"] = result.plate_number.replace(
                    "-", ""
                ).replace(".", "").replace(" ", "").strip()
            
            bbox_data = list(result.bbox.as_tuple) if result.bbox else [0, 0, 0, 0]
            
            # Insert vào database
            stmt = insert(Detection).values(
                lane_id=lane_id,
                image_key=image_key,
                raw_plate=result.plate_number,
                normalized_plate=plate_data["normalized"],
                confidence=result.confidence,
                bbox_x1=bbox_data[0],
                bbox_y1=bbox_data[1],
                bbox_x2=bbox_data[2],
                bbox_y2=bbox_data[3],
                processing_time_ms=result.processing_time_ms,
            )
            
            result_obj = db.execute(stmt)
            db.commit()
            
            return str(result_obj.inserted_primary_key[0])