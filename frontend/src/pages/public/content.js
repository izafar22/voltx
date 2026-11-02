import { CircuitBoard, PlugZap, Gauge, Cpu } from "lucide-react";
export const services = [
  {
    id: "pcb",
    icon: CircuitBoard,
    name: "PCB & control boards",
    short: "A closer look at the electronics behind the fault.",
    description:
      "Diagnosis and component-level repair of EV charger PCBs and control boards where technically feasible.",
    symptoms:
      "No power, intermittent operation, communication faults or visible board damage.",
    eligibility:
      "Assessment depends on board condition, fault isolation, component availability and the ability to test safely.",
  },
  {
    id: "ac",
    icon: PlugZap,
    name: "AC chargers",
    short: "Assessment for compatible home charging equipment.",
    description:
      "Repair enquiries for compatible AC chargers, including 3.3 kW and 7 kW / 7.4 kW models. These ratings are examples, not a guarantee of acceptance.",
    symptoms:
      "Charging fails to start, unexpected interruptions, indicator errors or connector-related symptoms.",
    eligibility:
      "Share the exact model and rating. Compatibility, safety condition and available parts determine acceptance.",
  },
  {
    id: "dc",
    icon: Gauge,
    name: "DC fast chargers",
    short: "Technical review before a repair is accepted.",
    description:
      "Diagnostic and repair enquiries for compatible DC fast charger electronics, subject to technical acceptance.",
    symptoms:
      "Fault codes, communication errors, power-module faults or charging interruptions.",
    eligibility:
      "Model, parts, safe testing facilities and technical acceptance must be confirmed before any repair proceeds.",
  },
  {
    id: "power",
    icon: Cpu,
    name: "Power supplies & electronics",
    short: "Explore repair options for supporting power modules.",
    description:
      "Assessment of auxiliary power supplies and power-electronics modules associated with charging equipment.",
    symptoms:
      "Loss of auxiliary power, unstable output or module fault indications.",
    eligibility:
      "Provide specifications and photos. Repair depends on module condition, replacement components and appropriate testing.",
  },
];
export const steps = [
  [
    "Tell us about the fault",
    "Submit the charger brand, model, type, rating, fault symptoms or codes, location and photos.",
  ],
  [
    "Initial technical assessment",
    "We review compatibility and repair feasibility, then confirm whether the enquiry can be accepted.",
  ],
  [
    "Inspection & your approval",
    "Following inspection, receive a quotation. You decide whether to authorize the proposed work.",
  ],
  [
    "Repair & testing",
    "Where feasible, we carry out the repair you approved and test the equipment within the accepted scope.",
  ],
  [
    "Return & documentation",
    "Arrange collection or return shipping and receive service documentation. Warranty terms apply only if specified in your quotation.",
  ],
];
export const faqs = [
  [
    "Can every EV charger be repaired?",
    "No. Repair feasibility depends on the model, fault, condition, parts and safe testing options. An assessment may recommend replacement when repair is not suitable.",
  ],
  [
    "Are you an authorized manufacturer service centre?",
    "RushX is an independent, multi-brand EV charger repair enquiry and electronics service. We do not claim manufacturer authorization.",
  ],
  [
    "Where is service available?",
    "We consider enquiries in Delhi NCR and Mumbai, plus eligible courier-based enquiries from across India. Availability and logistics must be confirmed during assessment. Bengaluru expansion is planned and is not currently offered.",
  ],
  [
    "Should I send my charger straight away?",
    "Please submit a repair enquiry first. Wait for technical acceptance and shipping instructions before sending equipment. Courier eligibility depends on the item, condition and safe transport arrangements.",
  ],
  [
    "What information should I prepare?",
    "Have your charger brand, model, type, power rating, fault symptoms or error codes, location and clear photos ready. Do not open or energize faulty equipment to gather information.",
  ],
  [
    "Will you repair it without my approval?",
    "No. Inspection and a quotation come before an approved repair. Review the proposed scope and charges before authorizing work.",
  ],
  [
    "Is a warranty included?",
    "Any warranty scope, duration and exclusions must be specified in your quotation. There is no blanket warranty promise.",
  ],
  [
    "How do I follow my repair?",
    "Sign in to your account and open Track a repair to view your existing repair requests and their progress.",
  ],
];
