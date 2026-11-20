import React, { useState } from 'react';
import { RepairWhatsAppConsentView } from '../components/RepairWhatsAppConsent';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export default { title: 'Patterns/Repair WhatsApp Updates', component: RepairWhatsAppConsentView };
function Preview(args) {
  const [value, setValue] = useState(null);
  return <Card className="max-w-2xl"><CardHeader><CardTitle>Repair milestone updates</CardTitle></CardHeader>
    <CardContent><RepairWhatsAppConsentView {...args} value={value} onChange={setValue} /></CardContent></Card>;
}
export const Verified = { render: Preview, args: { data: { available: true, destination: '••42', identity_key: 'sample', binding: 'storybook-only' } } };
export const VerificationRequired = { render: Preview, args: { data: { available: false, reason_code: 'verify_phone' }, canVerify: true, onVerify: () => {} } };
export const Unavailable = { render: Preview, args: { data: { available: false, reason_code: 'unavailable' } } };
