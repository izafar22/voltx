import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { homeFor } from "../components/ProtectedRoute";
import { Logo } from "../components/Logo";
import PhoneAuthForm from "../components/auth/PhoneAuthForm";
import {
  clearDestination,
  intendedDestination,
  rememberDestination,
} from "../lib/authDestination";
import { FEATURES } from "../config/features";
import "./Login.css";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading, login, authError, loadMe } = useAuth();
  const destination = intendedDestination(location.state);
  const complete = (data) => {
    clearDestination();
    login(data.user);
    navigate(destination || homeFor(data.user.role), { replace: true });
  };
  const google = () => {
    rememberDestination(destination);
    window.location.assign("/api/auth/google/login");
  };
  if (loading)
    return (
      <p role="status" className="p-8">
        Checking your session…
      </p>
    );
  if (user) {
    clearDestination();
    return <Navigate to={destination || homeFor(user.role)} replace />;
  }
  return (
    <main className="auth-layout">
      <aside className="auth-story">
        <Logo />
        <div>
          <span className="auth-story-tag">CHARGER CARE, SIMPLIFIED</span>
          <h2>
            {FEATURES.repair && !FEATURES.charging ? (
              <>
                Get your charger
                <br />
                working again.
              </>
            ) : (
              <>
                Your next charge,
                <br />
                within reach.
              </>
            )}
          </h2>
          <p>
            {FEATURES.repair && !FEATURES.charging
              ? "Expert repairs for AC, DC and portable chargers. One place to request service and follow every update."
              : "Find your next charge. Navigate, connect, and manage your charging across India."}
          </p>
          <div className="auth-story-details">
            <span>Any brand</span>
            <span>Clear updates</span>
            <span>One account</span>
          </div>
        </div>
        <small>RushX · Charger care that moves you forward</small>
      </aside>
      <section className="auth-main" aria-label="Sign in">
        <div className="auth-mobile-logo">
          <Logo />
        </div>
        <div className="auth-card">
          {authError && (
            <div role="alert" className="auth-session-error">
              {authError}
              <button type="button" onClick={loadMe}>
                Retry session check
              </button>
            </div>
          )}
          <PhoneAuthForm
            onComplete={complete}
            onGoogle={google}
            initialError={
              new URLSearchParams(window.location.search).has("google_error")
                ? "Google sign-in could not be completed. Please try again or use SMS."
                : ""
            }
          />
          <div className="auth-secure-note">
            <span aria-hidden="true">↗</span> Secure sign-in. Your repairs stay
            with you.
          </div>
        </div>
      </section>
    </main>
  );
}
