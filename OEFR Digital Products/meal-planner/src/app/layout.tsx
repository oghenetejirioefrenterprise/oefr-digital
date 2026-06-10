import type { Metadata } from "next";
import "./globals.css";
import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";

export const metadata: Metadata = {
  title: "MealCraft Pro — Weekly Meal Planner & Recipe Organizer | OEFR Digital",
  description: "Plan weekly meals, organize recipes, generate shopping lists, and hit your nutrition goals. One-time $27 — no subscription. The smart meal planning app for healthy living.",
  keywords: [
    "meal planner app",
    "weekly meal prep",
    "recipe organizer",
    "shopping list generator",
    "meal planning tool",
    "weekly meal plan",
    "nutrition tracker",
    "healthy meal planner",
    "recipe manager",
    "meal prep app",
  ],
  authors: [{ name: "OEFR Digital" }],
  creator: "OEFR Digital",
  publisher: "OEFR Digital",
  openGraph: {
    title: "MealCraft Pro — Weekly Meal Planner & Recipe Organizer",
    description: "Plan meals, organize recipes, and generate shopping lists. One-time $27 — no subscription, works offline.",
    url: "https://meal-planner-taupe-one.vercel.app",
    siteName: "OEFR Digital",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "MealCraft Pro — Weekly Meal Planner & Recipe Organizer",
    description: "Plan meals, organize recipes, and generate shopping lists. One-time $27 — no subscription, works offline.",
    creator: "@eustaceorukpe",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
  alternates: {
    canonical: "https://meal-planner-taupe-one.vercel.app",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500&family=Inter:wght@400;500;600&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
        <meta name="theme-color" content="#f4efe6" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'MealCraft Pro',
              description: 'Plan weekly meals, organize recipes, generate shopping lists, and hit nutrition goals. One-time purchase, works offline.',
              applicationCategory: 'HealthApplication',
              operatingSystem: 'Web',
              url: 'https://meal-planner-taupe-one.vercel.app',
              offers: {
                '@type': 'Offer',
                price: '27',
                priceCurrency: 'USD',
              },
              author: { '@type': 'Organization', name: 'OEFR Digital' },
            }),
          }}
        />
      </head>
      <body className="min-h-screen antialiased" style={{ background: '#f4efe6', color: '#1a1713', fontFamily: 'Inter, system-ui, sans-serif' }}>
        <ServiceWorkerRegistration />
        {children}
      </body>
    </html>
  );
}
