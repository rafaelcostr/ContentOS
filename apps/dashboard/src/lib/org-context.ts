const ORG_STORAGE_KEY = "contentos_org_id";

export function getOrganizationId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ORG_STORAGE_KEY);
}

export function setOrganizationId(orgId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ORG_STORAGE_KEY, orgId);
}

export function clearOrganizationId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ORG_STORAGE_KEY);
}
