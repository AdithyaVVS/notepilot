import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth.jsx";
import { WarmupBanner, useWarmup } from "./components/Warmup.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import NotePage from "./pages/NotePage.jsx";
import NotesPage from "./pages/NotesPage.jsx";
import TasksPage from "./pages/TasksPage.jsx";

function RequireAuth({ children }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <p className="status-line">Checking your session...</p>;
  if (status !== "authed") return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

export default function App() {
  const warmup = useWarmup();

  return (
    <>
      <WarmupBanner {...warmup} />
      <Routes>
        <Route path="/login" element={<AuthPage waking={warmup.phase === "waking"} />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <NotesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/notes/:id"
          element={
            <RequireAuth>
              <NotePage />
            </RequireAuth>
          }
        />
        <Route
          path="/tasks"
          element={
            <RequireAuth>
              <TasksPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
