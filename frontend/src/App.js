import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "@/context/ThemeContext";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import CustomerHome from "@/pages/customer/CustomerHome";
import ChargerPage from "@/pages/customer/ChargerPage";
import LivePage from "@/pages/customer/LivePage";
import WalletPage from "@/pages/customer/WalletPage";
import HistoryPage from "@/pages/customer/HistoryPage";
import OwnerDashboard from "@/pages/owner/OwnerDashboard";
import AdminDashboard from "@/pages/admin/AdminDashboard";

function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<Navigate to="/app" replace />} />

              <Route path="/app" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><CustomerHome /></ProtectedRoute>} />
              <Route path="/app/wallet" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><WalletPage /></ProtectedRoute>} />
              <Route path="/app/history" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><HistoryPage /></ProtectedRoute>} />
              <Route path="/app/charger/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><ChargerPage /></ProtectedRoute>} />
              <Route path="/app/live/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><LivePage /></ProtectedRoute>} />

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
