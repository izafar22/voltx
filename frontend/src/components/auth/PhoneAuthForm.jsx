import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";

export function normalizedPhone(value) {
  if (!/^\+?[\d\s()-]+$/.test(value.trim())) return null;
  let digits = value.replace(/[\s()+-]/g, "");
  if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
  return /^[6-9]\d{9}$/.test(digits) ? `+91${digits}` : null;
}
function message(error) {
  switch (error.response?.status) {
    case 400:
      return "Incorrect, expired, or already used code. Try again or request a new code.";
    case 401:
      return "Your verification expired. Please sign in again.";
    case 403:
      return "This account is unavailable for this action. Contact RushX support.";
    case 409:
      return "This number may already be linked to an account. Sign in with that number or contact RushX support for account recovery.";
    case 429:
      return "Too many requests or attempts. Wait before requesting a new code.";
    case 503:
      return "SMS delivery is unavailable. Please try again later.";
    default:
      return "We could not complete that request. Please try again.";
  }
}
export default function PhoneAuthForm({
  mode = "login",
  onComplete,
  onGoogle,
  initialError = "",
}) {
  const link = mode === "link";
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [name, setName] = useState("");
  const [challenge, setChallenge] = useState(null);
  const [grant, setGrant] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const [remaining, setRemaining] = useState(0);
  const lock = useRef(false),
    resendAt = useRef(0),
    attempted = useRef(null),
    input = useRef(null);
  const demo =
    process.env.NODE_ENV !== "production" &&
    process.env.REACT_APP_DEMO_AUTH === "true";
  const prefix = link ? "/auth/phone" : "/auth";
  useEffect(() => {
    input.current?.focus();
  }, [step]);
  useEffect(() => {
    const tick = () =>
      setRemaining(
        Math.max(0, Math.ceil((resendAt.current - Date.now()) / 1000)),
      );
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [challenge]);
  async function run(action) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      const retry = Number(e.response?.headers?.["retry-after"]);
      if (e.response?.status === 429 && retry > 0) {
        resendAt.current = Date.now() + retry * 1000;
        setRemaining(retry);
      }
      setError(message(e));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function requestCode(value = phone) {
    const normalized = normalizedPhone(value);
    if (!normalized) {
      setError("Enter a valid 10-digit Indian mobile number.");
      input.current?.focus();
      return;
    }
    if (remaining > 0) return;
    run(async () => {
      const { data } = await api.post(`${prefix}/request-otp`, {
        phone: normalized,
      });
      setPhone(normalized);
      setOtp("");
      attempted.current = null;
      setChallenge(data);
      resendAt.current = Date.now() + data.resend_after * 1000;
      setRemaining(data.resend_after);
      setStep("otp");
    });
  }
  async function verifyCode(code) {
    if (!/^\d{6}$/.test(code) || !challenge || lock.current) return;
    const attempt = `${challenge.challenge_id}:${code}`;
    if (attempted.current === attempt) return;
    attempted.current = attempt;
    await run(async () => {
      const { data } = await api.post(`${prefix}/verify-otp`, {
        phone,
        challenge_id: challenge.challenge_id,
        otp: code,
      });
      if (!link && data.registration_required) {
        setGrant(data.registration_token);
        setChallenge(null);
        setOtp("");
        setStep("register");
      } else {
        setStep("complete");
        onComplete(data);
      }
    });
  }
  // An entered, pasted or autofilled code is submitted once. A failed code is
  // never retried by rerenders/timer ticks; editing it explicitly enables retry.
  useEffect(() => {
    if (step === "otp" && otp.length === 6) verifyCode(otp);
    // Submission uses the current render's challenge and synchronous lock.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [otp, step, challenge]);
  function changeCode(value) {
    const next = value.replace(/\D/g, "").slice(0, 6);
    if (next !== otp) attempted.current = null;
    setOtp(next);
  }
  function changePhone() {
    setStep("phone");
    setOtp("");
    setChallenge(null);
    setGrant(null);
    setError("");
    setRemaining(0);
    resendAt.current = 0;
    attempted.current = null;
  }
  function register(event) {
    event.preventDefault();
    if (name.trim().length < 2 || name.trim().length > 100) {
      setError("Enter your full name (2–100 characters).");
      return;
    }
    run(async () => {
      const { data } = await api.post(
        "/auth/register-customer",
        { name: name.trim(), email: "" },
        { headers: { Authorization: `Bearer ${grant}` } },
      );
      setGrant(null);
      setStep("complete");
      onComplete(data);
    });
  }
  const description = error ? "auth-error" : undefined;
  return (
    <div className="phone-auth" aria-busy={busy}>
      {step === "phone" && (
        <form
          data-testid="phone-step"
          onSubmit={(e) => {
            e.preventDefault();
            requestCode();
          }}
          noValidate
        >
          <div className="auth-eyebrow">
            {link ? "YOUR ACCOUNT" : "WELCOME TO RUSHX"}
          </div>
          <h1>
            {link ? "Add your mobile number" : "A simpler way to sign in"}
          </h1>
          <p className="auth-description">
            {link
              ? "Verify a number to use it with your existing account. Your repair history stays with you."
              : "Enter your mobile number. We’ll send a secure code—no password needed."}
          </p>
          <label htmlFor="phone">Mobile number</label>
          <div className="auth-phone-input">
            <span aria-hidden="true">+91</span>
            <input
              ref={input}
              id="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel-national"
              placeholder="Mobile number"
              value={phone.startsWith("+91") ? phone.slice(3) : phone}
              maxLength={40}
              onChange={(e) => setPhone(e.target.value)}
              disabled={busy}
              aria-describedby={description}
              data-testid="phone-input"
            />
          </div>
          <button
            className="auth-primary"
            type="submit"
            disabled={busy || !phone.trim() || remaining > 0}
            data-testid="send-otp-btn"
          >
            {busy
              ? "Requesting code…"
              : remaining > 0
                ? `Continue in ${remaining}s`
                : "Continue"}
          </button>
          <p className="auth-note">
            This SMS is for account verification. WhatsApp repair updates are a
            separate, optional choice.
          </p>
          {onGoogle && (
            <>
              <div className="auth-divider">
                <span>OR</span>
              </div>
              <button
                className="auth-secondary"
                type="button"
                disabled={busy}
                onClick={onGoogle}
              >
                <span className="google-symbol" aria-hidden="true">
                  G
                </span>
                Continue with Google
              </button>
            </>
          )}
          {demo && !link && (
            <div className="auth-demo">
              <span>Development demo accounts</span>
              {[
                ["Admin", "+919000000001"],
                ["Owner", "+919000000002"],
                ["Customer", "+919000000003"],
              ].map(([label, number]) => (
                <button
                  key={label}
                  type="button"
                  disabled={busy || remaining > 0}
                  onClick={() => requestCode(number)}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </form>
      )}
      {step === "otp" && (
        <form
          data-testid="otp-step"
          onSubmit={(e) => {
            e.preventDefault();
            verifyCode(otp);
          }}
        >
          <div className="auth-eyebrow">ONE QUICK CHECK</div>
          <h1>Check your messages</h1>
          <p className="auth-description">
            Code requested for +91••••••{phone.slice(-4)}. Enter all six digits
            to continue.
          </p>
          <label htmlFor="otp">Six-digit code</label>
          <input
            ref={input}
            id="otp"
            className="auth-otp"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            value={otp}
            onChange={(e) => changeCode(e.target.value)}
            onPaste={(e) => {
              const code = e.clipboardData.getData("text").replace(/\s/g, "");
              if (/^\d{6}$/.test(code)) {
                e.preventDefault();
                changeCode(code);
              }
            }}
            disabled={busy}
            aria-describedby={description || "otp-help"}
            data-testid="otp-input"
          />
          <p id="otp-help" className="auth-note">
            Your code expires in 5 minutes. Verification starts automatically.
          </p>
          {demo && challenge?.demo_otp && (
            <p className="auth-note">Demo code: {challenge.demo_otp}</p>
          )}
          <button
            className="auth-primary"
            type="submit"
            disabled={busy || otp.length !== 6}
            data-testid="verify-otp-btn"
          >
            {busy ? "Verifying…" : "Verify code"}
          </button>
          <button
            className="auth-text-button auth-resend"
            type="button"
            disabled={busy || remaining > 0}
            onClick={() => requestCode()}
          >
            {remaining > 0 ? `Resend in ${remaining}s` : "Resend code"}
          </button>
        </form>
      )}
      {step === "register" && (
        <form data-testid="registration-step" onSubmit={register} noValidate>
          <div className="auth-eyebrow">ALMOST THERE</div>
          <h1>What should we call you?</h1>
          <p className="auth-description">
            Your number has been verified. Add your name to create your RushX
            account.
          </p>
          <label htmlFor="full-name">Full name</label>
          <input
            ref={input}
            id="full-name"
            autoComplete="name"
            value={name}
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
            disabled={busy}
            aria-describedby={description}
          />
          <button className="auth-primary" type="submit" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>
      )}
      {step === "complete" && (
        <p role="status">You’re verified. Taking you back…</p>
      )}
      <div className="auth-error-space" aria-live="polite">
        {error && (
          <p id="auth-error" role="alert">
            {error}
          </p>
        )}
      </div>
      {["otp", "register"].includes(step) && (
        <button
          className="auth-text-button"
          type="button"
          disabled={busy}
          onClick={changePhone}
          data-testid="change-phone-btn"
        >
          Edit mobile number
        </button>
      )}
    </div>
  );
}
