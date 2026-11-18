import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
  addressText,
  profileError,
  profileKey,
} from "../../lib/customerProfile";
import { useAuth } from "../../context/AuthContext";
import { CustomerShell } from "../../components/layout/CustomerShell";
import { CustomerAddressEditor } from "../../components/CustomerAddressEditor";
import { CustomerSignInMethods } from "../../components/CustomerSignInMethods";
import { CustomerPhoneLink } from "../../components/CustomerPhoneLink";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { CustomerAddressChoice as AddressChoice } from "../../components/CustomerAddressChoice";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";

export default function CustomerProfile() {
  const { user, setUser } = useAuth();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const query = useQuery({
    queryKey: profileKey(user),
    queryFn: async () => (await api.get("/customer/profile")).data,
  });
  const profile = query.data;
  const [name, setName] = useState(""),
    [message, setMessage] = useState(""),
    [error, setError] = useState("");
  const [busy, setBusy] = useState(false),
    [editor, setEditor] = useState(null),
    [phoneOpen, setPhoneOpen] = useState(false),
    [deleting, setDeleting] = useState(null);
  const lock = useRef(false);
  const savedName = profile?.user.name;
  useEffect(() => {
    if (savedName !== undefined) setName(savedName);
  }, [savedName]);
  const saved = (data) => {
    qc.setQueryData(profileKey(user), data);
    setUser(data.user);
    setMessage("Changes saved.");
    setError("");
  };
  const mutate = async (operation) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await operation();
    } catch (e) {
      setError(profileError(e));
      if (e.response?.status === 409) query.refetch();
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  const googleResult = params.get("google_link");
  const googleMessage = {
    success:
      "Google connected. You can now sign in with Google or WhatsApp OTP.",
    conflict:
      "This Google account is already linked to another RushX account. Choose a different Google account.",
    failed:
      "Google connection was cancelled or could not be verified. Please try again.",
  }[googleResult];
  const connectGoogle = () =>
    mutate(async () => {
      const { data } = await api.post("/auth/link/google/start");
      window.location.assign(data.url);
    });
  return (
    <CustomerShell>
      <div
        className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6"
        data-testid="customer-profile"
      >
        <div>
          <h1 className="font-display text-3xl font-semibold">Your profile</h1>
          <p className="text-muted-foreground mt-2">
            Manage your details, sign-in methods and saved addresses.
          </p>
        </div>
        {googleMessage && (
          <p role={googleResult === "success" ? "status" : "alert"}>
            {googleMessage}
          </p>
        )}
        {error && (
          <p role="alert" className="text-destructive">
            {error}
          </p>
        )}
        {message && <p role="status">{message}</p>}
        {query.isPending ? (
          <p role="status">Loading profile…</p>
        ) : query.isError ? (
          <div role="alert">
            <p>Unable to load your profile.</p>
            <Button variant="outline" onClick={() => query.refetch()}>
              Retry
            </Button>
          </div>
        ) : (
          profile && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Personal details</CardTitle>
                </CardHeader>
                <CardContent>
                  <form
                    className="space-y-4"
                    onSubmit={(e) => {
                      e.preventDefault();
                      mutate(async () =>
                        saved(
                          (await api.patch("/customer/profile", { name })).data,
                        ),
                      );
                    }}
                  >
                    <div className="space-y-2">
                      <Label htmlFor="profile-name">Full name</Label>
                      <Input
                        id="profile-name"
                        autoComplete="name"
                        required
                        minLength={2}
                        maxLength={100}
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                      />
                    </div>
                    <Button type="submit" disabled={busy}>
                      {busy ? "Saving…" : "Save name"}
                    </Button>
                  </form>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Contact and sign-in</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <CustomerSignInMethods
                    user={profile.user}
                    busy={busy}
                    onGoogle={connectGoogle}
                    onPhone={() => setPhoneOpen(true)}
                  />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Saved addresses</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {!profile.addresses.length && (
                    <p className="text-muted-foreground">
                      No saved addresses yet.
                    </p>
                  )}
                  {profile.addresses.map((a) => (
                    <article
                      key={a.id}
                      className="border-b border-border pb-4 space-y-3"
                    >
                      <h3 className="font-semibold">{a.label}</h3>
                      <p className="break-words">{addressText(a)}</p>
                      <p className="text-sm text-muted-foreground">
                        {[
                          profile.pickup_id === a.id && "Default pickup",
                          profile.delivery_id === a.id && "Default delivery",
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          disabled={busy}
                          onClick={() => setEditor({ address: a })}
                        >
                          Edit {a.label}
                        </Button>
                        <Button
                          variant="outline"
                          disabled={busy}
                          onClick={() =>
                            setDeleting({
                              address: a,
                              pickup_id:
                                profile.pickup_id === a.id
                                  ? null
                                  : profile.pickup_id,
                              delivery_id:
                                profile.delivery_id === a.id
                                  ? null
                                  : profile.delivery_id,
                            })
                          }
                        >
                          Delete {a.label}
                        </Button>
                        {["pickup", "delivery"]
                          .filter((k) => profile[`${k}_id`] !== a.id)
                          .map((k) => (
                            <Button
                              key={k}
                              variant="ghost"
                              disabled={busy}
                              onClick={() =>
                                mutate(async () =>
                                  saved(
                                    (
                                      await api.patch(
                                        "/customer/address-defaults",
                                        {
                                          revision: profile.revision,
                                          pickup_id: profile.pickup_id,
                                          delivery_id: profile.delivery_id,
                                          [`${k}_id`]: a.id,
                                        },
                                      )
                                    ).data,
                                  ),
                                )
                              }
                            >
                              Set default {k}
                            </Button>
                          ))}
                      </div>
                    </article>
                  ))}
                  <Button
                    disabled={busy || profile.addresses.length >= 20}
                    onClick={() => setEditor({})}
                  >
                    Add address
                  </Button>
                </CardContent>
              </Card>
              {editor && (
                <CustomerAddressEditor
                  onStale={() => query.refetch()}
                  profile={profile}
                  address={editor.address}
                  onClose={() => setEditor(null)}
                  onSaved={(data) => {
                    saved(data);
                    setEditor(null);
                  }}
                />
              )}
              {phoneOpen && (
                <CustomerPhoneLink
                  hasPhone={!!profile.user.phone}
                  onClose={() => setPhoneOpen(false)}
                  onSaved={(next) => {
                    saved({ ...profile, user: next });
                    setPhoneOpen(false);
                  }}
                />
              )}
              {deleting && (
                <Dialog
                  open
                  onOpenChange={(open) => {
                    if (!open && !busy) setDeleting(null);
                  }}
                >
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>
                        Delete {deleting.address.label}?
                      </DialogTitle>
                      <DialogDescription>
                        Select replacement defaults or choose later to clear
                        them. Existing repair addresses will remain unchanged.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      {["pickup", "delivery"].map((k) => (
                        <AddressChoice
                          key={k}
                          label={`Default ${k} after deletion`}
                          value={deleting[`${k}_id`]}
                          addresses={profile.addresses.filter(
                            (a) => a.id !== deleting.address.id,
                          )}
                          onChange={(value) =>
                            setDeleting({ ...deleting, [`${k}_id`]: value })
                          }
                          disabled={busy}
                        />
                      ))}
                      <p className="text-sm">
                        Choose later explicitly clears that default.
                      </p>
                      <Button
                        disabled={busy}
                        onClick={() =>
                          mutate(async () => {
                            saved(
                              (
                                await api.delete(
                                  `/customer/addresses/${deleting.address.id}`,
                                  {
                                    data: {
                                      revision: profile.revision,
                                      pickup_id: deleting.pickup_id,
                                      delivery_id: deleting.delivery_id,
                                    },
                                  },
                                )
                              ).data,
                            );
                            setDeleting(null);
                          })
                        }
                      >
                        Confirm deletion
                      </Button>
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() => setDeleting(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              )}
            </>
          )
        )}
      </div>
    </CustomerShell>
  );
}
