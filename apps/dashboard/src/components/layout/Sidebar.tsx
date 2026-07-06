"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Brain,
  Bot,
  Coins,
  Cpu,
  Database,
  FileText,
  FolderKanban,
  GitBranch,
  HardDrive,
  Images,
  Layers,
  LayoutDashboard,
  Library,
  Network,
  Package,
  Plug,
  Radio,
  ScanSearch,
  ScrollText,
  Share2,
  Settings,
  Split,
  Video,
  BarChart3,
  GraduationCap,
  TrendingUp,
  Gauge,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { OrgSelector } from "@/components/layout/OrgSelector";
import type { LucideIcon } from "lucide-react";

type NavItem = { href: string; label: string; icon: LucideIcon };

const sections: { title: string; items: NavItem[] }[] = [
  {
    title: "Produção",
    items: [
      { href: "/", label: "Painel", icon: LayoutDashboard },
      { href: "/executive", label: "Executive V4", icon: Gauge },
      { href: "/projects", label: "Projetos", icon: FolderKanban },
      { href: "/jobs", label: "Produção", icon: Activity },
      { href: "/videos", label: "Vídeos", icon: Video },
      { href: "/workflow", label: "Orquestração", icon: Workflow },
      { href: "/pipeline", label: "Fluxo", icon: GitBranch },
      { href: "/workflows/builder", label: "Workflow Builder", icon: Workflow },
      { href: "/agents", label: "Agentes", icon: Bot },
    ],
  },
  {
    title: "Conteúdo",
    items: [
      { href: "/assets", label: "Assets", icon: Images },
      { href: "/storage", label: "Armazenamento", icon: HardDrive },
      { href: "/content-sources", label: "Fontes", icon: Library },
      { href: "/clip-research", label: "Clip Research", icon: ScanSearch },
      { href: "/asset-collector", label: "Coletor", icon: Package },
    ],
  },
  {
    title: "IA & Plataforma",
    items: [
      { href: "/ai-gateway", label: "AI Gateway", icon: Network },
      { href: "/providers", label: "Provedores", icon: Plug },
      { href: "/models", label: "Modelos", icon: Cpu },
      { href: "/prompts", label: "Prompts", icon: FileText },
      { href: "/memory", label: "Memória", icon: Brain },
      { href: "/knowledge", label: "Knowledge Base", icon: Database },
      { href: "/viral", label: "Viral Intelligence", icon: Activity },
      { href: "/trend-forecast", label: "Trend Forecast", icon: TrendingUp },
      { href: "/ab-testing", label: "A/B Testing", icon: Split },
      { href: "/content-score", label: "Content Score", icon: Gauge },
      { href: "/specialists", label: "Specialists", icon: Bot },
      { href: "/multi-content", label: "Multi Content", icon: Layers },
      { href: "/learning", label: "Learning", icon: GraduationCap },
      { href: "/content-graph", label: "Content Graph", icon: Share2 },
      { href: "/cache", label: "Cache", icon: Database },
    ],
  },
  {
    title: "Observabilidade",
    items: [
      { href: "/analytics", label: "Análises", icon: BarChart3 },
      { href: "/costs", label: "Custos", icon: Coins },
      { href: "/events", label: "Eventos", icon: Radio },
      { href: "/logs", label: "Registros", icon: ScrollText },
      { href: "/plugins", label: "Publicação", icon: Share2 },
      { href: "/marketplace", label: "Marketplace", icon: Package },
      { href: "/settings", label: "Configurações", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card">
      <div className="flex h-16 items-center gap-3 border-b border-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary font-bold text-white">C</div>
        <div>
          <p className="text-sm font-semibold">ContentOS</p>
          <p className="text-xs text-muted-foreground">Fábrica de Vídeos IA</p>
        </div>
      </div>
      <OrgSelector />
      <nav className="flex-1 space-y-4 overflow-y-auto p-3">
        {sections.map((section) => (
          <div key={section.title}>
            <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              {section.title}
            </p>
            <div className="space-y-0.5">
              {section.items.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    isActive(href)
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-border p-3">
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted"
        >
          Sair
        </button>
        <Link
          href="/login"
          className="mt-1 flex items-center gap-2 rounded-md px-3 py-2 text-xs text-muted-foreground hover:bg-muted"
        >
          Trocar conta
        </Link>
      </div>
    </aside>
  );
}
