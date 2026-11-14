import React from "react";
import {
  RepairJourney,
  FAQ,
  ServiceCard,
} from "../components/patterns/RepairPatterns";
import { RepairStatus } from "../components/patterns/RepairStatus";
import { services, steps, faqs } from "../pages/public/content";
import { REPAIR_STATUS_LABEL } from "../lib/repairStatus";
export default {
  title: "Patterns/Repair",
  decorators: [
    (Story) => (
      <div className="rx-public">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          "The same pure components used in the public education pages and authenticated repair screens. Content comes from issue #13; statuses use existing backend enum labels. No real customer data or live APIs.",
      },
    },
  },
};
export const Service = {
  args: { index: 0 },
  argTypes: { index: { control: { type: "range", min: 0, max: 3, step: 1 } } },
  render: ({ index }) => (
    <section className="max-w-sm">
      <h2 className="sr-only">Repair service</h2>
      <ServiceCard service={services[index]} index={index} />
    </section>
  ),
};
export const Services = {
  render: () => (
    <section>
      <h2 className="ds-heading">What we assess</h2>
      <div className="rx-service-grid">
        {services.map((service, index) => (
          <ServiceCard key={service.id} service={service} index={index} />
        ))}
      </div>
    </section>
  ),
};
export const Journey = {
  render: () => (
    <section>
      <h2 className="ds-heading">A clear path forward</h2>
      <RepairJourney steps={steps} />
    </section>
  ),
};
export const Questions = {
  render: () => (
    <section className="max-w-3xl">
      <h2 className="ds-heading">Before you begin</h2>
      <FAQ items={faqs} />
    </section>
  ),
};
export const Status = {
  args: { status: "DIAGNOSING" },
  argTypes: {
    status: { control: "select", options: Object.keys(REPAIR_STATUS_LABEL) },
  },
  render: (args) => <RepairStatus {...args} />,
};
export const AllStatuses = {
  render: () => (
    <section className="ds-stack">
      <h2 className="ds-heading">Repair progress vocabulary</h2>
      <div className="ds-row">
        {Object.keys(REPAIR_STATUS_LABEL).map((status) => (
          <RepairStatus key={status} status={status} />
        ))}
      </div>
      <p className="ds-copy">
        Status is always expressed in text. Do not invent stages or rely on
        color alone.
      </p>
    </section>
  ),
};
