# Proposed Meta Utility templates

Status: owner explicitly approved all four submissions on 2026-11-20. Meta initially accepted all four as PENDING/UTILITY, then a subsequent API re-audit verified all four APPROVED/UTILITY in locale en. See active-template-approval.json. No lifecycle messages sent. No existing approved template or OTP configuration will be edited. All four use locale `en`, Utility category and the static footer `evchargerrepair.in`. Examples in the JSON are synthetic.

## rushx_awaiting_shipment_v1

Hello {{1}},

Your RushX repair request {{2}} has been accepted for inspection.

Please pack your EV charger securely and send it to:
{{3}}

Include your repair request number with the package and share the courier tracking details after dispatch.

Acceptance is for inspection only. We will share a repair estimate for your approval before paid repair work begins.

## rushx_repair_completed_balance_v1

Hello {{1}}, repair work for {{2}} is complete. The outstanding balance is INR {{3}}. Please check your RushX dashboard or contact support for payment instructions. We will share return-shipment details once dispatch is confirmed.

## rushx_repair_completed_no_balance_v1

Hello {{1}}, repair work for {{2}} is complete. No payment is currently due. We will share return-shipment details once dispatch is confirmed.

## rushx_payment_received_v1

Hello {{1}}, RushX has verified payment for repair {{2}}. Amount received: INR {{3}}. Reference: {{4}}. Thank you.

The positive and zero-balance completion variants are mutually exclusive. These four templates plus five compatible existing approved templates cover eight milestones and nine active variants. Existing standalone completion/payment-pending templates remain unused by lifecycle v3. Approval of a submission is not a claim of Meta approval or permission to send before readiness.
