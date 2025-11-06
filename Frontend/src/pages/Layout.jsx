import { Outlet, useLocation } from "react-router-dom";
import Navbar from "../component/Navbar";
import './Layout.css';

export default function Layout() {
  const location = useLocation();
  const isNewPage = location.pathname === '/'; // 只匹配 /new

  return (
    <div className="layout-container">
      <Navbar />
      <main className={`content-area ${isNewPage ? "center-content" : ""}`}>
        <Outlet />
      </main>
    </div>
  );
}
