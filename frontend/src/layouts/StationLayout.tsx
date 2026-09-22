import { Outlet } from "react-router-dom";
export default function StationLayout() {
  return <div style={{
    minHeight: "100vh"
  }}><header style={{
      padding: "14px 20px",
      borderBottom: "1px solid #555"
    }}><strong>VisionPark</strong> · Station Operator</header><main><Outlet /></main></div>;
}
