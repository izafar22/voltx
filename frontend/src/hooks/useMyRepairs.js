import { useQuery } from "@tanstack/react-query";
import { listRepairs } from "../lib/repairApi";

// Shared with repair history and invalidated by existing repair status actions.
export function useMyRepairs() {
  return useQuery({
    queryKey: ["repairs-mine"],
    queryFn: () => listRepairs("mine"),
  });
}
