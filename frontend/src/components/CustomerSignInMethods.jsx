import { Button } from "./ui/button";

export function CustomerSignInMethods({ user, busy, onGoogle, onPhone }) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="font-medium">Google email</h3>
        {user.google_linked ? (
          <>
            <p className="break-words">{user.email}</p>
            <p className="text-sm text-muted-foreground">
              Verified by Google · Read-only
            </p>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Verify your email with Google. You can then sign in with Google or
              your WhatsApp number.
            </p>
            <Button variant="outline" disabled={busy} onClick={onGoogle}>
              Connect Google account
            </Button>
          </>
        )}
      </div>
      <div className="space-y-2">
        <h3 className="font-medium">WhatsApp mobile number</h3>
        <p>
          {user.phone_verified
            ? `${user.phone} · Verified`
            : "No verified mobile number"}
        </p>
        <p className="text-sm text-muted-foreground">
          Verify this number through WhatsApp. You can then use it for repair
          contact and sign-in.
        </p>
        <Button variant="outline" disabled={busy} onClick={onPhone}>
          {user.phone ? "Change number" : "Add and verify mobile number"}
        </Button>
      </div>
      <p className="text-sm font-medium">
        You can sign in with{" "}
        {user.google_linked && user.phone_verified
          ? "Google or WhatsApp OTP"
          : user.google_linked
            ? "Google"
            : "WhatsApp OTP"}
        .
      </p>
    </div>
  );
}
