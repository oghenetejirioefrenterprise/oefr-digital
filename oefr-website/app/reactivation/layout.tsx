import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Database Reactivation Service — Recover Revenue from Cold Contacts | OEFR",
  description:
    "A 14-day, done-for-you reactivation pilot for independent fitness businesses. Test a compliant win-back campaign with your approved dormant-contact list.",
  keywords: [
    "database reactivation",
    "email reactivation service",
    "cold contact recovery",
    "CRM reactivation",
    "win back clients",
    "dormant list reactivation",
    "lead reactivation",
    "recover lost clients",
    "email re-engagement",
    "cold lead nurturing",
  ],
  openGraph: {
    title: "Database Reactivation — Recover Revenue Hiding in Your CRM",
    description:
      "Run a focused, 14-day win-back pilot using contacts your business already has permission to reach.",
    url: "https://www.oefrenterprise.com/reactivation",
    siteName: "OEFR Digital",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Database Reactivation — Recover Revenue Hiding in Your CRM",
    description:
      "A focused 14-day reactivation pilot for independent gyms and fitness studios.",
    creator: "@eustaceorukpe",
  },
  alternates: {
    canonical: "https://www.oefrenterprise.com/reactivation",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "Service",
  name: "Database Reactivation Service",
  provider: {
    "@type": "Organization",
    name: "OEFR Digital",
    url: "https://www.oefrenterprise.com",
  },
  description:
    "A done-for-you 14-day reactivation pilot for independent gyms and fitness studios using an approved dormant-contact list.",
  offers: {
    "@type": "Offer",
    price: "500",
    priceCurrency: "USD",
    description: "One-time founding-pilot fee",
  },
  areaServed: "United States",
  url: "https://www.oefrenterprise.com/reactivation",
};

export default function ReactivationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {children}
    </>
  );
}
