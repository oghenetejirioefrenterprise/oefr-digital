import type { Metadata } from "next";
import Link from "next/link";
import { blogPosts } from "@/lib/blog-posts";

export const metadata: Metadata = {
  title: "Journal — OEFR Digital | AI Prompts, Productivity & Digital Tools",
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
    title: "Journal — OEFR Digital",
    description: "Expert guides on AI prompts, productivity tools, and digital products.",
    url: "https://www.oefrenterprise.com/blog",
    siteName: "OEFR Digital",
    type: "website",
  },
  alternates: { canonical: "https://www.oefrenterprise.com/blog" },
};

export default function BlogPage() {
  return (
    <>
      <section className="px-6 sm:px-10 lg:px-16 pt-20 pb-16 border-b border-[#d8cdb8]">
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-7">
          Journal · {blogPosts.length} posts
        </div>
        <h1 className="font-[family-name:var(--font-fraunces)] font-light text-[56px] sm:text-[80px] lg:text-[104px] tracking-[-0.04em] leading-[0.95] mb-7 text-[#1a1713]">
          Notes from the{" "}
          <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">studio</em>.
        </h1>
        <p className="text-[18px] lg:text-[20px] leading-[1.55] text-[#3d362c] max-w-[720px]">
          Practical guides on AI prompts, productivity tools, and building smarter workflows. Written by engineers, backed by real experience.
        </p>
      </section>

      <section className="px-6 sm:px-10 lg:px-16 py-16">
        <div className="border-t border-[#1a1713]">
          {blogPosts.map((post, idx) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group grid grid-cols-[60px_1fr_auto] md:grid-cols-[80px_1fr_180px_140px_60px] gap-4 md:gap-6 items-center py-7 border-b border-[#d8cdb8] hover:bg-[#ece3cf] hover:-mx-6 hover:px-6 lg:hover:-mx-16 lg:hover:px-16 transition-[background,margin,padding] duration-150"
            >
              <span className="font-[family-name:var(--font-mono)] text-xs text-[#7a6f5c]">
                {String(idx + 1).padStart(3, "0")}
              </span>
              <div>
                <h2 className="font-[family-name:var(--font-fraunces)] text-xl md:text-[26px] leading-tight tracking-tight group-hover:text-[#a66a2c] transition-colors">
                  {post.title}
                </h2>
                <p className="mt-2 md:hidden text-xs text-[#3d362c] line-clamp-2">{post.excerpt}</p>
              </div>
              <span className="hidden md:block font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] uppercase text-[#7a6f5c]">
                {post.publishedDate}
              </span>
              <span className="hidden md:block font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] uppercase text-[#7a6f5c]">
                {post.readingTime}
              </span>
              <span className="font-serif text-xl text-right group-hover:text-[#a66a2c] group-hover:translate-x-1 transition-all">→</span>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
