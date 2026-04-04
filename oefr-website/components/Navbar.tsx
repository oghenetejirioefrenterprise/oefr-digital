"use client";

import Link from "next/link";
import { useState } from "react";

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-800/60 bg-[#0a0f1e]/95 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-bold text-sm shadow-lg shadow-blue-500/25 group-hover:shadow-blue-500/40 transition-shadow">
              OD
            </div>
            <span className="text-lg font-bold text-white">
              OEFR <span className="text-blue-400">Digital</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Products
            </Link>
            <Link
              href="/about"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              About
            </Link>
            <Link
              href="/blog"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Blog
            </Link>
            <Link
              href="/reactivation"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              DB Reactivation
            </Link>
            <a
              href="mailto:oghenetejiri@oefrenterprise.com"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Contact
            </a>
            <a
              href="https://netarch-pro.vercel.app"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-lg shadow-blue-600/25"
            >
              Browse Products →
            </a>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden text-slate-400 hover:text-white transition-colors p-2"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            <div className="space-y-1.5">
              <span
                className={`block h-0.5 w-6 bg-current transition-transform ${menuOpen ? "translate-y-2 rotate-45" : ""}`}
              />
              <span
                className={`block h-0.5 w-6 bg-current transition-opacity ${menuOpen ? "opacity-0" : ""}`}
              />
              <span
                className={`block h-0.5 w-6 bg-current transition-transform ${menuOpen ? "-translate-y-2 -rotate-45" : ""}`}
              />
            </div>
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden border-t border-slate-800 py-4 space-y-3">
            <Link
              href="/"
              onClick={() => setMenuOpen(false)}
              className="block text-sm text-slate-400 hover:text-white transition-colors py-2"
            >
              Products
            </Link>
            <Link
              href="/about"
              onClick={() => setMenuOpen(false)}
              className="block text-sm text-slate-400 hover:text-white transition-colors py-2"
            >
              About
            </Link>
            <Link
              href="/blog"
              onClick={() => setMenuOpen(false)}
              className="block text-sm text-slate-400 hover:text-white transition-colors py-2"
            >
              Blog
            </Link>
            <Link
              href="/reactivation"
              onClick={() => setMenuOpen(false)}
              className="block text-sm text-slate-400 hover:text-white transition-colors py-2"
            >
              DB Reactivation
            </Link>
            <a
              href="mailto:oghenetejiri@oefrenterprise.com"
              className="block text-sm text-slate-400 hover:text-white transition-colors py-2"
            >
              Contact
            </a>
            <a
              href="https://netarch-pro.vercel.app"
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white text-center hover:bg-blue-500 transition-colors"
            >
              Browse Products →
            </a>
          </div>
        )}
      </div>
    </nav>
  );
}
