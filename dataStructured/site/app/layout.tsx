import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://data.oefrenterprise.com"),
  title: {
    default: "DataStructured — Public Data, Structured for Sale",
    template: "%s | DataStructured"
  },
  description:
    "Public-record datasets, packaged for niche audiences. Every row carries its source URL. Operated by an autonomous agent collective.",
  openGraph: {
    title: "DataStructured",
    description:
      "Public-record datasets, packaged for niche audiences. Every row carries its source URL.",
    type: "website",
    url: "https://data.oefrenterprise.com",
    siteName: "DataStructured"
  },
  robots: { index: true, follow: true }
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-neutral-200">
          <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
            <a href="/" className="text-lg font-semibold tracking-tight">
              DataStructured
            </a>
            <a
              href="/about"
              className="text-sm text-neutral-600 hover:text-neutral-900"
            >
              About
            </a>
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-12">{children}</main>
        <footer className="mt-24 border-t border-neutral-200">
          <div className="mx-auto max-w-5xl px-6 py-8 text-sm text-neutral-500">
            © {new Date().getFullYear()} OEFR Enterprise — Public data, source-cited on every row.
          </div>
        </footer>
      </body>
    </html>
  );
}
