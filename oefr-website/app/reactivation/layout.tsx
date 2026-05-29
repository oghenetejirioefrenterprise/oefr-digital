import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Database Reactivation Service — Recover Revenue from Cold Contacts | OEFR",
  description:
    "Done-for-you email reactivation service. We turn your dormant CRM contacts into warm leads and recovered revenue — no ads, no new leads needed. Results in 2 weeks.",
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
      "We reactivate your cold contacts and put money back in your business. No new ads. No new leads. Just results from what you already have.",
    url: "https://www.oefrenterprise.com/reactivation",
    siteName: "OEFR Digital",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Database Reactivation — Recover Revenue Hiding in Your CRM",
    description:
      "Done-for-you email reactivation. Turn dormant CRM contacts into revenue — results in 2 weeks.",
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
    "Done-for-you email reactivation service for gyms, dental clinics, and service businesses. We recover revenue from cold contacts with no new ad spend.",
  offers: {
    "@type": "Offer",
    price: "750",
    priceCurrency: "USD",
    description: "Setup fee plus 300 per month management",
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
