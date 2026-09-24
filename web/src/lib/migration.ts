import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Implementation, type MigrationRoute } from "./api";

export function useMigration() {
  return useQuery({ queryKey: ["migration"], queryFn: api.migration, staleTime: 5_000 });
}

export function useFlip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ routeKey, implementation }: { routeKey: string; implementation: Implementation }) =>
      api.setImplementation(routeKey, implementation),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["migration"] }),
  });
}

/** `f?p=APP:PAGE:SESSION::NO::ITEMS:VALUES` — session 0 lets ORDS start a new public APEX session. */
export function apexPageUrl(route: MigrationRoute, items: Record<string, string | number> = {}) {
  const names = Object.keys(items);
  const base = route.apex_url.replace(/:(\d+)$/, ":$1:0::NO::");
  if (names.length === 0) return base;
  return `${base}${names.join(",")}:${names.map((n) => items[n]).join(",")}`;
}
