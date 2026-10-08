import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// Shared with repair history and invalidated by existing repair status actions.
export function useMyRepairs() {
  return useQuery({
    queryKey: ["repairs-mine"],
    queryFn: async () => (await api.get("/repairs", { params: { scope: "mine" } })).data,
  });
}
