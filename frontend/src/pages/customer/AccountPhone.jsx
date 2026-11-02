import { useAuth } from "../../context/AuthContext";
import { CustomerShell } from "../../components/layout/CustomerShell";
import PhoneAuthForm from "../../components/auth/PhoneAuthForm";
import "../Login.css";
export default function AccountPhone() {
  const { user, setUser } = useAuth();
  return (
    <CustomerShell>
      <section className="p-5 sm:p-8 max-w-xl">
        <h1 className="text-2xl font-semibold">Account phone</h1>
        {user?.phone_verified ? (
          <div className="mt-6">
            <p role="status">Your mobile number is verified.</p>
            <p className="mt-2">{user.phone}</p>
            <p className="text-sm text-muted-foreground mt-4">
              Contact RushX support if you need to change this number. WhatsApp
              updates remain your choice on each repair request.
            </p>
          </div>
        ) : (
          <div className="phone-link-panel">
            <PhoneAuthForm
              mode="link"
              onComplete={(data) =>
                setUser((current) =>
                  current?.user_id === data.user.user_id ? data.user : current,
                )
              }
            />
          </div>
        )}
      </section>
    </CustomerShell>
  );
}
