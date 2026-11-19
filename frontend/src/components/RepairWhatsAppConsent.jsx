import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { Button } from './ui/button';
import { CustomerPhoneLink } from './CustomerPhoneLink';

export function RepairWhatsAppConsentView({ data, value, onChange, disabled = false, canVerify = false, onVerify }) {
  return <section className="mt-6 space-y-3" aria-label="WhatsApp repair updates">
    <div className="flex items-start gap-3">
      <input id="whatsapp-opt-in" data-testid="whatsapp-opt-in" type="checkbox"
        checked={!!value} disabled={disabled || !data?.available}
        onChange={e => onChange(e.target.checked ? data : null)}
        aria-describedby="whatsapp-consent-help" className="h-5 w-5 shrink-0 self-start" />
      <label htmlFor="whatsapp-opt-in" className="min-w-0 break-normal">Send me WhatsApp updates about this repair</label>
    </div>
    <p id="whatsapp-consent-help" className="text-sm text-muted-foreground">
      {data?.available ? `Updates go to your verified mobile ending ${data.destination}. Stop them from repair details at any time.` :
        data?.reason_code === 'verify_phone' ? 'Verify your mobile before selecting WhatsApp updates.' :
          'WhatsApp updates are currently unavailable. You can still follow your repair in your account.'}
    </p>
    {data?.reason_code === 'verify_phone' && canVerify &&
      <Button type="button" variant="outline" disabled={disabled} onClick={onVerify}>Verify mobile for updates</Button>}
    <p className="text-sm text-muted-foreground">Receive key repair, estimate, payment and return-shipment updates. Signing in by WhatsApp does not enable these updates automatically.</p>
  </section>;
}

export function RepairWhatsAppConsent({ value, onChange, disabled = false }) {
  const { user, beginUserUpdate } = useAuth();
  const [verifying, setVerifying] = useState(false);
  const capability = useQuery({ queryKey: ['repair-whatsapp-capability', user?.user_id, user?.phone],
    enabled: !!user, retry: false, refetchOnWindowFocus: false,
    queryFn: async () => (await api.get('/customer/whatsapp-capability')).data });
  const data = capability.data;
  useEffect(() => {
    if (value && (!data?.available || value.identity_key !== data.identity_key)) onChange(null);
  }, [data?.available, data?.identity_key, value, onChange]);
  return <>
    <RepairWhatsAppConsentView data={data} value={value} onChange={onChange} disabled={disabled}
      canVerify={user?.role === 'customer'} onVerify={() => setVerifying(true)} />
    {verifying && <CustomerPhoneLink hasPhone={!!user?.phone} onClose={() => setVerifying(false)} onBeginSave={beginUserUpdate}
      onSaved={async (updatedUser, complete) => { if (complete && !complete(updatedUser)) return; setVerifying(false); onChange(null); await capability.refetch(); }} />}
  </>;
}
