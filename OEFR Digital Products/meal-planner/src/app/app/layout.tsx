"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { hasAccess } from "@/lib/storage";
import {
  Leaf,
  Calendar,
  ChefHat,
  ShoppingCart,
  Settings,
  LogOut,
  Menu,
  X,
} from "lucide-react";

const navItems = [
  { href: "/app", icon: Calendar, label: "Meal Planner" },
  { href: "/app/recipes", icon: ChefHat, label: "Recipes" },
  { href: "/app/shopping", icon: ShoppingCart, label: "Shopping List" },
  { href: "/app/settings", icon: Settings, label: "Settings" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    // Skip auth check for gate and success pages
    if (pathname === "/app/gate" || pathname === "/app/success") {
      setChecked(true);
      return;
    }
    if (!hasAccess()) {
      router.replace("/app/gate");
    } else {
      setChecked(true);
    }
  }, [router, pathname]);

  if (!checked) {
    return (
      <div className="min-h-screen bg-navy-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-lime-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Gate and success pages render without sidebar
  if (pathname === "/app/gate" || pathname === "/app/success") {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-navy-950 flex">
      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-navy-900 border-r border-navy-700 flex flex-col transition-transform duration-200 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-navy-700 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-lime-500 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-navy-950" />
            </div>
            <span className="font-bold text-white">
              MealCraft<span className="text-lime-400">Pro</span>
            </span>
          </Link>
          <button
            className="lg:hidden text-slate-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  active
                    ? "bg-lime-500/10 text-lime-400 border border-lime-500/20"
                    : "text-slate-400 hover:text-white hover:bg-navy-800"
                }`}
              >
                <item.icon className="w-5 h-5 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-navy-700">
          <Link
            href="/"
            className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-500 hover:text-white hover:bg-navy-800 text-sm transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 bg-navy-900 border-b border-navy-700">
          <button onClick={() => setSidebarOpen(true)} className="text-slate-400 hover:text-white">
            <Menu className="w-5 h-5" />
          </button>
          <span className="text-white font-semibold text-sm">
            {navItems.find((n) => n.href === pathname)?.label ?? "MealCraft Pro"}
          </span>
        </div>

        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
