"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Leaf, Menu, X } from "lucide-react";
import { useState } from "react";

const links = [
  { href: "/", label: "Home" },
  { href: "/demo", label: "Try Demo" },
  { href: "/app", label: "My Planner" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-navy-950/90 backdrop-blur-md border-b border-navy-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-lime-500 flex items-center justify-center">
            <Leaf className="w-5 h-5 text-navy-950" />
          </div>
          <span className="font-bold text-lg text-white group-hover:text-lime-400 transition-colors">
            MealCraft<span className="text-lime-400">Pro</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`text-sm font-medium transition-colors ${
                pathname === l.href
                  ? "text-lime-400"
                  : "text-slate-300 hover:text-white"
              }`}
            >
              {l.label}
            </Link>
          ))}
          <Link
            href="/#pricing"
            className="px-4 py-2 rounded-lg bg-lime-500 text-navy-950 text-sm font-bold hover:bg-lime-400 transition-colors"
          >
            Get Access — $14
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden text-slate-300 hover:text-white"
          onClick={() => setOpen(!open)}
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-navy-900 border-t border-navy-800 px-4 py-4 space-y-3">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={`block text-sm font-medium py-2 ${
                pathname === l.href ? "text-lime-400" : "text-slate-300"
              }`}
            >
              {l.label}
            </Link>
          ))}
          <Link
            href="/#pricing"
            onClick={() => setOpen(false)}
            className="block w-full text-center px-4 py-2 rounded-lg bg-lime-500 text-navy-950 text-sm font-bold"
          >
            Get Access — $14
          </Link>
        </div>
      )}
    </nav>
  );
}
