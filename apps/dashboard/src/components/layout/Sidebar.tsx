"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Brain,
  Bot,
  ChevronDown,
  Clapperboard,
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
  Mic,
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
  CalendarDays,
  MessageCircle,
  TrendingUp,
  Gauge,
  Hash,
  LineChart,
  Target,
  Palette,
  Users,
  Workflow,
  Factory,
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
      { href: "/executive", label: "Command Center", icon: Gauge },
      { href: "/projects", label: "Projetos", icon: FolderKanban },
      { href: "/jobs", label: "Produção", icon: Activity },
      { href: "/factory", label: "Content Factory", icon: Factory },
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
      { href: "/voice-studio", label: "Voice Studio", icon: Mic },
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
      { href: "/retention", label: "Retention Engine", icon: LineChart },
      { href: "/seo", label: "SEO Engine", icon: Hash },
      { href: "/director", label: "AI Director", icon: Clapperboard },
      { href: "/creative-memory", label: "Creative Memory", icon: Brain },
      { href: "/specialists", label: "Specialists", icon: Bot },
      { href: "/multi-content", label: "Multi Content", icon: Layers },
      { href: "/learning", label: "Learning", icon: GraduationCap },
      { href: "/community", label: "Community Agent", icon: MessageCircle },
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
  {
    title: "Growth",
    items: [
      { href: "/growth", label: "Growth AI", icon: Target },
      { href: "/brand", label: "Brand", icon: Palette },
      { href: "/channels", label: "Canais", icon: Share2 },
      { href: "/competitors", label: "Concorrentes", icon: Users },
      { href: "/strategy", label: "Estratégia", icon: CalendarDays },
      { href: "/calendar", label: "Calendário", icon: CalendarDays },
      { href: "/performance", label: "Performance", icon: LineChart },
      { href: "/recommendations", label: "Recomendações", icon: Hash },
      { href: "/history", label: "Histórico", icon: ScrollText },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const activeSection = useMemo(
    () => sections.find((section) => section.items.some((item) => isActivePath(pathname, item.href)))?.title,
    [pathname]
  );
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(sections.map((section) => [section.title, section.title === "Produção"]))
  );

  useEffect(() => {
    if (!activeSection) return;
    setOpenSections((current) => ({ ...current, [activeSection]: true }));
  }, [activeSection]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  function isActive(href: string) {
    return isActivePath(pathname, href);
  }

  function toggleSection(title: string) {
    setOpenSections((current) => ({ ...current, [title]: !current[title] }));
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
      <nav className="flex-1 space-y-1 overflow-y-auto p-2">
        {sections.map((section) => (
          <div key={section.title} className="rounded-md">
            <button
              type="button"
              onClick={() => toggleSection(section.title)}
              className={cn(
                "flex h-9 w-full items-center justify-between rounded-md px-3 text-left text-xs font-semibold uppercase text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                activeSection === section.title && "text-primary"
              )}
            >
              <span>{section.title}</span>
              <span className="flex items-center gap-2">
                <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {section.items.length}
                </span>
                <ChevronDown
                  className={cn("h-3.5 w-3.5 transition-transform", openSections[section.title] && "rotate-180")}
                />
              </span>
            </button>
            {openSections[section.title] && (
              <div className="mt-1 space-y-0.5 pb-1">
                {section.items.map(({ href, label, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      "flex h-8 items-center gap-3 rounded-md px-3 text-sm transition-colors",
                      isActive(href)
                        ? "bg-primary/15 text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="truncate">{label}</span>
                  </Link>
                ))}
              </div>
            )}
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

function isActivePath(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
