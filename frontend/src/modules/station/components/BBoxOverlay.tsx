type Props = {
  bbox: [number, number, number, number] | null;
  sourceWidth: number;
  sourceHeight: number;
};
export default function BBoxOverlay({
  bbox,
  sourceWidth,
  sourceHeight
}: Props) {
  if (!bbox || sourceWidth <= 0 || sourceHeight <= 0) return null;
  const [x1, y1, x2, y2] = bbox;
  if (x2 <= x1 || y2 <= y1) return null;
  return <svg data-testid="bbox-overlay" viewBox={`0 0 ${sourceWidth} ${sourceHeight}`} preserveAspectRatio="xMidYMid meet" style={{
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none"
  }}>
    <rect data-testid="bbox-rect" x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke="red" strokeWidth="5" vectorEffect="non-scaling-stroke" />
  </svg>;
}
