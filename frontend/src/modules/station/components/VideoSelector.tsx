type Props = {
  onVideoSelected: (file: File, url: string) => void;
};
export default function VideoSelector({
  onVideoSelected
}: Props) {
  return <label style={{
    display: "grid",
    gap: 6
  }} htmlFor="video-file">
    <strong>Video MP4</strong>
    <input id="video-file" aria-label="Video MP4" type="file" accept="video/mp4,.mp4" onChange={event => {
      const file = event.target.files?.[0];
      if (!file) return;
      const valid = file.type === "video/mp4" || file.name.toLowerCase().endsWith(".mp4");
      if (!valid) {
        window.alert("File không hợp lệ. Vui lòng chọn video MP4.");
        event.target.value = "";
        return;
      }
      onVideoSelected(file, URL.createObjectURL(file));
    }} />
  </label>;
}
