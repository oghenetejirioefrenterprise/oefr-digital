import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { blogPosts, getPostBySlug, getAllSlugs } from "@/lib/blog-posts";

const BASE_URL = "https://www.oefrenterprise.com";

export function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) {
    return { title: "Post not found — OEFR Digital" };
  }
  const url = `${BASE_URL}/blog/${post.slug}`;
  return {
    title: `${post.title} — OEFR Digital`,
    description: post.description,
    keywords: post.keywords,
    authors: [{ name: post.author }],
    openGraph: {
      title: post.title,
      description: post.description,
      url,
      siteName: "OEFR Digital",
      type: "article",
      publishedTime: post.publishedDate,
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.description,
    },
    alternates: { canonical: url },
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) notFound();

  const url = `${BASE_URL}/blog/${post.slug}`;
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.description,
    author: { "@type": "Organization", name: post.author },
    publisher: {
      "@type": "Organization",
      name: "OEFR Digital",
      url: BASE_URL,
    },
    datePublished: post.publishedDate,
    dateModified: post.publishedDate,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    keywords: post.keywords.join(", "),
  };

  const faqSchema =
    post.faq && post.faq.length > 0
      ? {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: post.faq.map((item) => ({
            "@type": "Question",
            name: item.q,
            acceptedAnswer: { "@type": "Answer", text: item.a },
          })),
        }
      : null;

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      {faqSchema && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
        />
      )}

      {/* Header — site cream theme */}
      <section className="px-6 sm:px-10 lg:px-16 pt-16 pb-12 border-b border-[#d8cdb8]">
        <Link
          href="/blog"
          className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] hover:text-[#a66a2c] transition-colors"
        >
          ← Journal
        </Link>
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.16em] uppercase text-[#7a6f5c] mt-7 mb-5">
          {post.publishedDate} · {post.readingTime} · {post.author}
        </div>
        <h1 className="font-[family-name:var(--font-fraunces)] font-light text-[40px] sm:text-[56px] lg:text-[72px] tracking-[-0.035em] leading-[1.0] mb-6 text-[#1a1713] max-w-[980px]">
          {post.title}
        </h1>
        <p className="text-[18px] lg:text-[20px] leading-[1.55] text-[#3d362c] max-w-[760px]">
          {post.excerpt}
        </p>
      </section>

      {/* Body — dark reading panel (post content HTML uses slate/amber classes) */}
      <section className="px-6 sm:px-10 lg:px-16 py-14 bg-[#14110d]">
        <article className="mx-auto max-w-[760px]">
          <div dangerouslySetInnerHTML={{ __html: post.content }} />
        </article>
      </section>

      {/* FAQ — visible content backing the FAQPage JSON-LD (rich-result compliant) */}
      {post.faq && post.faq.length > 0 ? (
        <section className="px-6 sm:px-10 lg:px-16 py-14 border-t border-[#d8cdb8]">
          <div className="mx-auto max-w-[760px]">
            <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-8">
              Frequently asked questions
            </div>
            <div className="space-y-8">
              {post.faq.map((item) => (
                <div key={item.q}>
                  <h2 className="font-[family-name:var(--font-fraunces)] text-[22px] lg:text-[26px] tracking-[-0.02em] leading-[1.2] text-[#1a1713] mb-3">
                    {item.q}
                  </h2>
                  <p className="text-[16px] lg:text-[17px] leading-[1.6] text-[#3d362c]">
                    {item.a}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {/* CTA */}
      <section className="px-6 sm:px-10 lg:px-16 py-14 border-t border-[#d8cdb8]">
        <div className="mx-auto max-w-[760px]">
          <a
            href={post.cta.href}
            className="inline-flex items-center gap-3 rounded-full bg-[#1a1713] px-8 py-4 text-[15px] font-medium text-[#f5efe2] hover:bg-[#a66a2c] transition-colors"
          >
            {post.cta.text}
            {post.cta.discount ? (
              <span className="rounded-full bg-[#a66a2c] px-3 py-1 text-xs">
                {post.cta.discount}
              </span>
            ) : null}
            <span aria-hidden>→</span>
          </a>

          {post.relatedProducts.length > 0 ? (
            <div className="mt-16">
              <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-6">
                Related
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {post.relatedProducts.map((rp) => (
                  <a
                    key={rp.href}
                    href={rp.href}
                    className="block rounded-xl border border-[#d8cdb8] p-5 hover:border-[#a66a2c] hover:bg-[#ece3cf] transition-colors"
                  >
                    <div className="font-[family-name:var(--font-fraunces)] text-lg text-[#1a1713] mb-2">
                      {rp.name}
                    </div>
                    <p className="text-sm leading-relaxed text-[#3d362c]">
                      {rp.description}
                    </p>
                  </a>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}
