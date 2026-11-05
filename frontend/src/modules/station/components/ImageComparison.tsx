import { DetectionImage } from '../../../components/DetectionImage'

type Props = { entryImage?: string | null; exitImage?: string | null; plate: string }

export default function ImageComparison({ entryImage, exitImage, plate }: Props) {
  return <section className="card scan-video" aria-label="Đối chiếu ảnh xe vào và ra">
    <div className="scan-card-head"><div><span className="card-kicker">ĐỐI CHIẾU XE</span><h3>{plate}</h3></div></div>
    <div className="station-image-comparison">
      <figure><figcaption>Ảnh lúc vào</figcaption>{entryImage ? <DetectionImage src={entryImage} /> : <p role="status">Không có ảnh lúc vào (check-in thủ công).</p>}</figure>
      <figure><figcaption>Ảnh lúc ra</figcaption>{exitImage ? <DetectionImage src={exitImage} /> : <p role="status">Chưa có ảnh lúc ra. Chọn ảnh hoặc chụp khung hình để đối chiếu.</p>}</figure>
    </div>
  </section>
}
