import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import useAuthStore from "./store/authStore";

// Layouts
import AppLayout from "./components/layout/AppLayout";
import AuthLayout from "./components/layout/AuthLayout";

// Auth pages
import LoginPage    from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";

// Role dashboards
import OwnerDashboard   from "./pages/owner/OwnerDashboard";
import ManagerDashboard from "./pages/manager/ManagerDashboard";
import MemberDashboard  from "./pages/member/MemberDashboard";

// Feature pages
import TasksPage          from "./pages/tasks/TasksPage";
import AgentsPage         from "./pages/agents/AgentsPage";
import IntegrationsPage   from "./pages/integrations/IntegrationsPage";
import ApprovalsPage   from "./pages/approvals/ApprovalsPage";
import ReportsPage     from "./pages/reports/ReportsPage";
import NewReportPage   from "./pages/reports/NewReportPage";
import DiscussionsPage from "./pages/discussions/DiscussionsPage";
import TeamPage            from "./pages/team/TeamPage";
import OrganizationsPage  from "./pages/organizations/OrganizationsPage";
import ChatPage           from "./pages/chat/ChatPage";

// ── Role-aware home page ─────────────────────────────────────────────────────
function HomeDashboard() {
  const { user } = useAuthStore();
  if (!user) return null;
  if (user.role === "member" || user.role === "viewer") return <MemberDashboard />;
  if (user.role === "manager")                          return <ManagerDashboard />;
  return <OwnerDashboard />;   // owner / admin
}

// ── Guards ───────────────────────────────────────────────────────────────────
function RequireAuth({ children }) {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function RequireGuest({ children }) {
  const { isAuthenticated } = useAuthStore();
  return !isAuthenticated ? children : <Navigate to="/" replace />;
}

// Only owners and admins can access a route
function RequireOwner({ children }) {
  const { user } = useAuthStore();
  if (!user) return null;
  return user.role === "owner" || user.role === "admin"
    ? children
    : <Navigate to="/" replace />;
}

// ── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const { loadUser, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) loadUser();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        {/* Auth routes */}
        <Route element={<RequireGuest><AuthLayout /></RequireGuest>}>
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* App routes */}
        <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
          {/* Role-aware home */}
          <Route path="/" element={<HomeDashboard />} />

          {/* Shared pages */}
          <Route path="/tasks"       element={<TasksPage />} />
          <Route path="/reports"     element={<ReportsPage />} />
          <Route path="/reports/new" element={<NewReportPage />} />
          <Route path="/discussions" element={<DiscussionsPage />} />
          <Route path="/chat"        element={<ChatPage />} />
          <Route path="/team"        element={<TeamPage />} />

          {/* Manager+ only */}
          <Route path="/approvals" element={<ApprovalsPage />} />

          {/* Admin/Owner only */}
          <Route path="/organizations" element={<RequireOwner><OrganizationsPage /></RequireOwner>} />
          <Route path="/agents"        element={<RequireOwner><AgentsPage /></RequireOwner>} />
          <Route path="/integrations"  element={<RequireOwner><IntegrationsPage /></RequireOwner>} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
