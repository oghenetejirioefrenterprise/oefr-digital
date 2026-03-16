export type Category = "Finance & Productivity" | "IT & Engineering" | "Career & Business" | "Coming Soon";

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  link: string;
  category: Category;
  tags: string[];
  featured?: boolean;
  comingSoon?: boolean;
  rating: number;
  reviews: number;
  badge?: string;
}

export const products: Product[] = [
  {
    id: "budgetwise-pro",
    name: "BudgetWise Pro",
    description:
      "A powerful personal budget tracker that helps you manage expenses, set savings goals, and get notified before bills are due. Beautiful charts, zero subscriptions.",
    price: 29,
    link: "https://budget-tracker-lime-psi.vercel.app",
    category: "Finance & Productivity",
    tags: ["budget", "expense tracking", "savings goals", "bill reminders"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "Popular",
  },
  {
    id: "invoiceflow",
    name: "InvoiceFlow",
    description:
      "Generate professional invoices in seconds. Built for freelancers — line items, client management, multiple templates, and PDF exports. $37 once vs $20/mo competitors.",
    price: 37,
    link: "https://invoice-generator-nine-psi.vercel.app",
    category: "Finance & Productivity",
    tags: ["invoicing", "freelance", "billing", "PDF"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "New",
  },
  {
    id: "resumeforge",
    name: "ResumeForge",
    description:
      "Build stunning, ATS-friendly resumes with a 7-step wizard. 4 professional templates, live preview, PDF export. Land your next role faster.",
    price: 29,
    link: "https://resume-builder-delta-puce.vercel.app",
    category: "Career & Business",
    tags: ["resume", "job search", "career", "ATS"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "New",
  },
  {
    id: "postify",
    name: "Postify Content Calendar",
    description:
      "Plan, schedule, and organize social media content across all platforms. Visual calendar, hashtag research, content ideas bank. $29 once vs $99/mo Hootsuite.",
    price: 29,
    link: "https://content-calendar-vert.vercel.app",
    category: "Career & Business",
    tags: ["social media", "content planning", "marketing", "scheduling"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "New",
  },
  {
    id: "enterprise-network-hld",
    name: "Enterprise Network HLD Template",
    description:
      "Professional High-Level Design template for enterprise network architectures. Used by senior network engineers at Fortune 500 companies.",
    price: 39,
    link: "https://netarch-pro.vercel.app",
    category: "IT & Engineering",
    tags: ["network design", "HLD", "enterprise", "architecture"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "Best Seller",
  },
  {
    id: "network-documentation-bundle",
    name: "Network Documentation Bundle",
    description:
      "Complete network documentation pack — IP addressing, topology diagrams, runbooks, and change management templates. Everything a network team needs.",
    price: 59,
    link: "https://netarch-pro.vercel.app",
    category: "IT & Engineering",
    tags: ["documentation", "network", "templates", "runbooks"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "Bundle",
  },
  {
    id: "network-security-audit",
    name: "Network Security Audit Checklist",
    description:
      "A comprehensive security audit checklist for network infrastructure. Covers firewalls, access controls, VPN, segmentation, and compliance.",
    price: 24,
    link: "https://netarch-pro.vercel.app",
    category: "IT & Engineering",
    tags: ["security", "audit", "compliance", "firewall"],
    rating: 0,
    reviews: 0,
  },
  {
    id: "routing-protocol-cheatsheets",
    name: "Routing Protocol Cheat Sheets",
    description:
      "Quick-reference cheat sheets for OSPF, BGP, EIGRP, IS-IS, and more. Perfect for cert prep, interviews, and on-the-job troubleshooting.",
    price: 14,
    link: "https://netarch-pro.vercel.app",
    category: "IT & Engineering",
    tags: ["routing", "BGP", "OSPF", "certifications"],
    rating: 0,
    reviews: 0,
    badge: "Top Rated",
  },
  {
    id: "ansible-network-automation",
    name: "Ansible Network Automation Pack",
    description:
      "Production-ready Ansible playbooks for network automation — device config backups, compliance checks, bulk changes, and reporting.",
    price: 49,
    link: "https://netarch-pro.vercel.app",
    category: "IT & Engineering",
    tags: ["ansible", "automation", "network", "devops"],
    rating: 0,
    reviews: 0,
  },
  {
    id: "mealcraft",
    name: "MealCraft Pro",
    description:
      "Plan weekly meals with drag-and-drop, auto-generate shopping lists, and track nutrition. 52 built-in recipes with dietary filters. $27 once vs $9/mo competitors.",
    price: 27,
    link: "https://meal-planner-taupe-one.vercel.app",
    category: "Finance & Productivity",
    tags: ["meal planning", "nutrition", "health", "recipes"],
    featured: true,
    rating: 0,
    reviews: 0,
    badge: "New",
  },
  {
    id: "vaultpass",
    name: "VaultPass Password Manager",
    description:
      "Real AES-256 encryption, not toy crypto. Generate, store, and manage passwords offline. Security dashboard spots weak & reused passwords. $19 once vs $3-5/mo competitors.",
    price: 19,
    link: "https://password-vault-kappa-ten.vercel.app",
    category: "Finance & Productivity",
    tags: ["security", "passwords", "privacy", "encryption"],
    rating: 0,
    reviews: 0,
    badge: "New",
  },
  {
    id: "signaturecraft",
    name: "SignatureCraft",
    description:
      "Professional email signatures in 60 seconds. 4 templates, email-client compatible HTML, copy-paste into Gmail/Outlook. $9 once vs $3-5/mo competitors.",
    price: 9,
    link: "https://email-signature-liart.vercel.app",
    category: "Career & Business",
    tags: ["email", "signature", "professional", "branding"],
    rating: 0,
    reviews: 0,
    badge: "Popular",
  },
  {
    id: "subtracker",
    name: "SubTracker",
    description:
      "Track every subscription you pay for. See total spend, get renewal alerts, audit unused services. Privacy-first — zero bank access needed. $19 once vs $4-12/mo Rocket Money.",
    price: 19,
    link: "https://subscription-tracker-mu-two.vercel.app",
    category: "Finance & Productivity",
    tags: ["subscriptions", "finance", "budgeting", "savings"],
    rating: 0,
    reviews: 0,
    badge: "New",
  },
];

export const comingSoonProducts: Product[] = [
  {
    id: "habit-tracker",
    name: "HabitForge — Habit Tracker",
    description:
      "Build and track daily habits with streaks, analytics, and accountability. Visual calendar, customizable reminders, and progress insights.",
    price: 0,
    link: "#",
    category: "Coming Soon",
    tags: ["habits", "productivity", "self-improvement"],
    comingSoon: true,
    rating: 0,
    reviews: 0,
  },
  {
    id: "flashcard-app",
    name: "CardMaster — Flashcard Study App",
    description:
      "Spaced repetition flashcards for students and professionals. Create decks, track mastery, and study smarter with science-backed algorithms.",
    price: 0,
    link: "#",
    category: "Coming Soon",
    tags: ["education", "flashcards", "study", "learning"],
    comingSoon: true,
    rating: 0,
    reviews: 0,
  },
];

export const allCategories = ["All", "Finance & Productivity", "Career & Business", "IT & Engineering", "Coming Soon"] as const;
export type FilterCategory = (typeof allCategories)[number];
