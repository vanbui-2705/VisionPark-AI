import { t as translate } from "../../../lib/i18n"
import type { ApiError } from "../types";
type Props = {
  error: ApiError | null;
  onRetry: () => void;
};
const messageFor = (error: ApiError) => {
  switch (error.status) {
    case 401:
      return translate("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.");
    case 403:
      return translate("Bạn không có quyền sử dụng chức năng Station.");
    case 409:
      return error.code === "DETECTION_ALREADY_CONFIRMED" ? translate("Detection này đã được xác nhận trước đó.") : error.message;
    case 422:
      return error.message || translate("Ảnh hoặc dữ liệu gửi lên không hợp lệ.");
    case 503:
      return translate("Dịch vụ ALPR hiện chưa sẵn sàng.");
    case 408:
      return translate("Yêu cầu ALPR bị timeout.");
    case 0:
      return translate("Không thể kết nối tới Backend.");
    default:
      return error.message;
  }
};
export default function ErrorPanel({
  error,
  onRetry
}: Props) {
  if (!error) return null;
  const retryable = error.status === 408 || error.status === 503 || error.status === 0;
  return <div role="alert" style={{
    marginTop: 16,
    padding: 14,
    border: "2px solid #b42318",
    borderRadius: 8
  }}>
    <strong>{translate("Lỗi Station")}</strong><p>{messageFor(error)}</p><small>{error.code} ({error.status})</small>
    {retryable && <div style={{
      marginTop: 10
    }}><button type="button" onClick={onRetry}>{translate("↻ Thử lại")}</button></div>}
  </div>;
}
