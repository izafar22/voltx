export const lifecycleStages = [
  {
    id: "request",
    short: "Request",
    title: "Request received",
    description:
      "Your charger details, symptoms, measurements and useful photos are recorded. RushX reviews the enquiry before asking you to hand over anything.",
    location: "With customer",
    nextActor: "RushX reviews",
    control:
      "Wait for RushX review. Inspection instructions follow only after acceptance.",
    message:
      "We received your repair request. Our team will review it before confirming the next step.",
  },
  {
    id: "accepted",
    short: "Accepted",
    title: "Accepted for inspection",
    description:
      "RushX accepts the charger for inspection and provides the approved hand-off or shipping instructions.",
    location: "With customer",
    nextActor: "Customer hand-off",
    control:
      "Follow only the approved hand-off instructions in your RushX account. Acceptance permits inspection, not priced repair work.",
    message:
      "Your charger has been accepted for inspection. Follow the approved instructions in your RushX account.",
  },
  {
    id: "received",
    short: "Received",
    title: "Charger received",
    description:
      "RushX records physical receipt before inspection and diagnosis begin.",
    location: "RushX intake",
    nextActor: "RushX diagnoses",
    control:
      "RushX now inspects the charger and identifies a feasible repair scope where possible.",
    message:
      "We have received your charger at RushX. Inspection can now begin.",
  },
  {
    id: "estimate",
    short: "Estimate",
    title: "Estimate ready",
    description:
      "Diagnosis has produced a proposed repair scope and price. You decide whether work proceeds.",
    location: "RushX",
    nextActor: "Customer decides",
    control:
      "Review the estimate and choose Approve or Decline. This explanation cannot change a real repair.",
    message:
      "Your estimate is ready. Review it and choose Approve or Decline.",
    decision: true,
  },
  {
    id: "approved",
    short: "Approved",
    title: "Approval recorded",
    description:
      "Your decision is recorded. Only work covered by the approved estimate moves ahead.",
    location: "RushX repair",
    nextActor: "RushX repairs",
    control: "RushX begins only the work you approved.",
    message:
      "Your estimate approval has been recorded. We will proceed with the approved work.",
  },
  {
    id: "result",
    short: "Result",
    title: "Repair result and balance",
    description:
      "RushX records the result after testing and shows the verified balance position.",
    location: "RushX testing",
    nextActor: "Customer reviews",
    control: "Review the repair result and verified balance in your account.",
    message:
      "Repair is complete. Your verified balance is available in your RushX account.",
  },
  {
    id: "payment",
    short: "Payment",
    title: "Payment received",
    description:
      "A payment acknowledgement appears only after RushX verifies the receipt.",
    location: "RushX dispatch",
    nextActor: "RushX prepares return",
    control: "RushX prepares the charger for return dispatch.",
    message: "We have verified your payment. Thank you.",
  },
  {
    id: "returned",
    short: "Returned",
    title: "Return dispatched",
    description:
      "Courier and tracking facts appear when the charger is actually dispatched.",
    location: "With courier",
    nextActor: "Customer receives",
    control: "Follow the courier details in your RushX account.",
    message:
      "Your charger has been dispatched. Courier and tracking details are now available.",
  },
];
