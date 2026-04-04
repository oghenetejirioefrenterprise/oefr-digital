import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "OEFR Digital — Productivity Apps & Digital Tools | No Subscriptions",
  description: "Smart digital tools and productivity apps built by engineers. Budget trackers, invoice generators, resume builders, and more — one-time purchase, no subscription ever.",
  keywords: [
    "digital tools",
    "productivity apps",
    "one-time purchase software",
    "no subscription tools",
    "budget tracker",
    "invoice generator",
    "resume builder",
    "meal planner",
    "password manager",
    "content calendar",
    "email signature generator",
    "subscription tracker",
    "network engineering templates",
    "ansible automation",
    "BGP cheat sheet",
    "OSPF reference",
    "network documentation",
    "CCIE study",
    "network security checklist",
    "enterprise HLD template",
  ],
  authors: [{ name: "OEFR Digital" }],
  creator: "OEFR Digital",
  publisher: "OEFR Digital",
  openGraph: {
    title: "OEFR Digital — Productivity Apps & Digital Tools",
    description: "Smart digital tools built by engineers — budget trackers, invoice generators, resume builders & more. One-time purchase, no subscription.",
    url: "https://www.oefrenterprise.com",
    siteName: "OEFR Digital",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "OEFR Digital — Productivity Apps & Digital Tools",
    description: "Smart digital tools built by engineers — budget trackers, invoice generators, resume builders & more. One-time purchase, no subscription.",
    creator: "@eustaceorukpe",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
  alternates: {
    canonical: "https://www.oefrenterprise.com",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Organization',
              name: 'OEFR Digital',
              description: 'Smart digital tools and productivity apps built by engineers — one-time purchase, no subscription ever.',
              url: 'https://www.oefrenterprise.com',
              sameAs: ['https://twitter.com/eustaceorukpe'],
              offers: {
                '@type': 'AggregateOffer',
                offerCount: '9',
                lowPrice: '9',
                highPrice: '37',
                priceCurrency: 'USD',
              },
            }),
          }}
        />
      </head>
      <body className="min-h-screen bg-[#0a0f1e] text-slate-100 antialiased">
        <Navbar />
        <main className="min-h-screen">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
