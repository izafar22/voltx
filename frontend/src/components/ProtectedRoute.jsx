import { rememberRepairDestination } from "../lib/repairDestination";
import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const homeFor = (role) => (role === "admin" ? "/admin" : role === "owner" ? "/owner" : "/app");

export const ProtectedRoute = ({ children, roles }) => {
  const location = useLocation();
  const { user, loading, authError, loadMe } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-accent" /></div>;
  if (!user && authError) return <div role="alert" className="p-6"><p>{authError}</p><button onClick={loadMe} className="mt-3 underline">Retry</button></div>;
  if (!user) { rememberRepairDestination(location.pathname); return <Navigate to="/login" replace />; }
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return children;
};

export { homeFor };
