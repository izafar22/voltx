import { Badge } from "../ui/badge";
import { REPAIR_STATUS_LABEL } from "../../lib/repairStatus";
export function RepairStatus({ status, ...props }) {
  return (
    <Badge variant="secondary" className="rounded-full" {...props}>
      {REPAIR_STATUS_LABEL[status] || status}
    </Badge>
  );
}
