import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-slate-800/60 bg-[#080d1a] mt-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Brand */}
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-bold text-xs">
              OD
            </div>
            <span className="font-bold text-white">
              OEFR <span className="text-blue-400">Digital</span>
            </span>
          </div>

          {/* Links */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500">
            <Link href="/about" className="hover:text-slate-300 transition-colors">
              About
            </Link>
            <Link href="/terms" className="hover:text-slate-300 transition-colors">
              Terms
            </Link>
            <Link href="/privacy" className="hover:text-slate-300 transition-colors">
              Privacy
            </Link>
            <a
              href="mailto:oghenetejiri@oefrenterprise.com"
              className="hover:text-slate-300 transition-colors"
            >
              Contact
            </a>
          </div>

          {/* Badges & Copyright */}
          <div className="flex items-center gap-4">
            <a href="https://fazier.com" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
              <img
                src="https://fazier.com/api/v1/badges/embed/default?url=https://oefrenterprise.com"
                alt="Featured on Fazier"
                width="150"
                height="54"
                style={{ height: '28px', width: 'auto' }}
              />
            </a>
            <p className="text-sm text-slate-600">
              © 2026 OEFR Digital. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
