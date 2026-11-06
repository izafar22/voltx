import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "@/context/ThemeContext";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import PublicPage from "./pages/public/PublicPage";
import Login from "@/pages/Login";
import CustomerHome from "@/pages/customer/CustomerHome";
import ChargerPage from "@/pages/customer/ChargerPage";
import LivePage from "@/pages/customer/LivePage";
import WalletPage from "@/pages/customer/WalletPage";
import HistoryPage from "@/pages/customer/HistoryPage";
import RepairNew from "@/pages/customer/RepairNew";
import RepairDetail from "@/pages/customer/RepairDetail";
import RepairsList from "@/pages/customer/RepairsList";
import RepairAdmin from "@/pages/admin/RepairAdmin";

import { FEATURES } from "./config/features";

function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              {["/", "/services", "/about", "/how-it-works", "/faq"].map(path => <Route key={path} path={path} element={<PublicPage />} />)}

              <Route path="/app" element={<ProtectedRoute roles={["customer", "admin", "owner"]}><CustomerHome /></ProtectedRoute>} />
              <Route path="/app/wallet" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.wallet ? <WalletPage /> : <Navigate to="/app" replace />}</ProtectedRoute>} />
              <Route path="/app/history" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.charging ? <HistoryPage /> : <Navigate to="/app" replace />}</ProtectedRoute>} />
              <Route path="/app/charger/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.charging ? <ChargerPage /> : <Navigate to="/app" replace />}</ProtectedRoute>} />
              <Route path="/app/live/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.charging ? <LivePage /> : <Navigate to="/app" replace />}</ProtectedRoute>} />

              <Route path="/repairs" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.repair ? <RepairsList /> : <Navigate to="/app" replace />}</ProtectedRoute>} />
              <Route path="/repairs/new" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.repair ? <RepairNew /> : <Navigate to="/app" replace />}</ProtectedRoute>} />
              <Route path="/repairs/:id" element={<ProtectedRoute roles={["customer", "admin", "owner"]}>{FEATURES.repair ? <RepairDetail /> : <Navigate to="/app" replace />}</ProtectedRoute>} />

              <Route path="/owner" element={<ProtectedRoute roles={["owner", "admin"]}><Navigate to="/app" replace /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><Navigate to="/admin/repairs" replace /></ProtectedRoute>} />
              <Route path="/admin/repairs" element={<ProtectedRoute roles={["admin"]}><RepairAdmin /></ProtectedRoute>} />

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
