import { Sidebar } from "@/components/layout/Sidebar";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Sidebar />
      <main className="pl-64 min-h-screen">
        <AuthGuard>{children}</AuthGuard>
      </main>
    </>
  );
}
