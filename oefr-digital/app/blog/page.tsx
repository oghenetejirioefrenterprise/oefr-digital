import type { Metadata } from "next";
import Link from "next/link";
import { blogPosts } from "@/lib/blog-posts";

export const metadata: Metadata = {
  title: "Blog — OEFR Digital | AI Prompts, Productivity & Digital Tools",
  description:
    "Expert guides on AI prompts, productivity tools, budget trackers, and digital products. Actionable tips from engineers who build the tools.",
  keywords: [
    "AI prompts",
    "productivity tools",
    "budget tracker",
    "ChatGPT tips",
    "digital tools blog",
    "network engineering AI",
  ],
  openGraph: {
    title: "Blog — OEFR Digital",
    description:
      "Expert guides on AI prompts, productivity tools, and digital products.",
    url: "https://oefrenterprise.com/blog",
    siteName: "OEFR Digital",
    type: "website",
  },
  alternates: {
    canonical: "https://oefrenterprise.com/blog",
  },
};

const icons = ["🤖", "⚡", "💰"];

export default function BlogPage() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8">
      {/* Hero */}
      <div className="relative mx-auto max-w-4xl text-center mb-16">
        <div className="pointer-events-none absolute inset-0 -top-20">
          <div className="absolute left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full bg-blue-600/8 blur-3xl" />
        </div>
        <div className="relative">
          <div className="mb-4 inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400">
            <span className="mr-2">📝</span>
            Insights & Guides
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4">
            OEFR Digital{" "}
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Blog
            </span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            Practical guides on AI prompts, productivity tools, and building
            smarter workflows. Written by engineers, backed by real experience.
          </p>
        </div>
      </div>

      {/* Posts Grid */}
      <div className="mx-auto max-w-6xl grid gap-8 md:grid-cols-2 lg:grid-cols-3">
        {blogPosts.map((post, idx) => (
          <Link
            key={post.slug}
            href={`/blog/${post.slug}`}
            className="group flex flex-col rounded-2xl border border-slate-800 bg-slate-900/50 p-6 hover:border-blue-500/40 hover:bg-slate-900/80 transition-all duration-300"
          >
            {/* Icon */}
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 text-2xl">
              {icons[idx % icons.length]}
            </div>

            {/* Title */}
            <h2 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors mb-2 line-clamp-2">
              {post.title}
            </h2>

            {/* Excerpt */}
            <p className="text-sm text-slate-400 mb-4 line-clamp-3 flex-1">
              {post.excerpt}
            </p>

            {/* Meta */}
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{post.publishedDate}</span>
              <span>{post.readingTime}</span>
            </div>

            {/* Read link */}
            <div className="mt-4 text-sm font-medium text-blue-400 group-hover:text-blue-300 transition-colors">
              Read Post →
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
