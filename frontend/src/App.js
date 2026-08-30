import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { ThemeProvider } from "@/context/ThemeContext";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { ProtectedRoute, homeFor } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import CustomerHome from "@/pages/customer/CustomerHome";
import ChargerPage from "@/pages/customer/ChargerPage";
import LivePage from "@/pages/customer/LivePage";
import WalletPage from "@/pages/customer/WalletPage";
import HistoryPage from "@/pages/customer/HistoryPage";
import RepairNew from "@/pages/customer/RepairNew";
import RepairDetail from "@/pages/customer/RepairDetail";
import OwnerDashboard from "@/pages/owner/OwnerDashboard";
import AdminDashboard from "@/pages/admin/AdminDashboard";

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-accent" /></div>;
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<RootRedirect />} />

              <Route path="/app" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><CustomerHome /></ProtectedRoute>} />
              <Route path="/app/wallet" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><WalletPage /></ProtectedRoute>} />
              <Route path="/app/history" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><HistoryPage /></ProtectedRoute>} />
              <Route path="/app/charger/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><ChargerPage /></ProtectedRoute>} />
              <Route path="/app/live/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><LivePage /></ProtectedRoute>} />

              <Route path="/repairs/new" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><RepairNew /></ProtectedRoute>} />
              <Route path="/repairs/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><RepairDetail /></ProtectedRoute>} />

              <Route path="/owner" element={<ProtectedRoute roles={["owner", "admin"]}><OwnerDashboard /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><AdminDashboard /></ProtectedRoute>} />

              <Route path="*" element={<Navigate to="/app" replace />} />
            </Routes>
            <Toaster position="top-center" richColors />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}

export default App;
