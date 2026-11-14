import { useId } from "react";
import { ArrowRight, Wrench } from "lucide-react";
import { Button } from "../ui/button";
import { Card } from "../ui/card";

export function RepairCTA({ onRequest }) {
  const titleId = useId();
  return (
    <section
      className="dashboard-repair-hero dashboard-card"
      aria-labelledby={titleId}
    >
      <div>
        <p className="text-sm text-muted-foreground mb-2">
          Independent, multi-brand assessment
        </p>
        <h2 id={titleId} className="font-display text-2xl font-semibold">
          Repair when possible. Replace when necessary.
        </h2>
        <p className="text-sm text-muted-foreground mt-3">
          Request an assessment and track your repair. Acceptance depends on the
          model, fault, parts and safe testing options.
        </p>
      </div>
      <Button
        data-testid="repair-charger-btn"
        onClick={onRequest}
        className="dashboard-repair-cta"
      >
        <Wrench aria-hidden="true" className="h-5 w-5 mr-2 shrink-0" />
        Repair a Charger
        <ArrowRight aria-hidden="true" className="h-4 w-4 ml-2 shrink-0" />
      </Button>
    </section>
  );
}
export function EmptyState({
  title,
  description,
  icon: Icon = Wrench,
  action,
}) {
  return (
    <Card className="p-6">
      <Icon aria-hidden="true" className="h-6 w-6 text-muted-foreground mb-3" />
      <p className="font-medium">{title}</p>
      <p className="text-sm text-muted-foreground mt-2">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </Card>
  );
}
