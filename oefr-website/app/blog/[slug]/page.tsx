import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPostBySlug, getAllSlugs } from "@/lib/blog-posts";
import NewsletterSignup from "@/components/NewsletterSignup";

interface BlogSignupCopy {
  eyebrow: string;
  heading: React.ReactNode;
  subheading: string;
  buttonLabel: string;
  successCopy: string;
}

const DEFAULT_BLOG_SIGNUP: BlogSignupCopy = {
  eyebrow: "Stay in the loop",
  heading: (
    <>
      Get the next launch <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">free</em>. Plus a sample tab from the next pack.
    </>
  ),
  subheading:
    "One short email when something ships. No spam, no upsells, no recycled AI takes — just the work.",
  buttonLabel: "Notify me",
  successCopy: "✓ You're on the list",
};

const BLOG_SIGNUP_OVERRIDES: Record<string, BlogSignupCopy> = {
  "airbnb-turnover-sop-damage-disputes": {
    eyebrow: "Pre-order — ships mid-May",
    heading: (
      <>
        Get notified the day the <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">8-tab pack</em> ships.
      </>
    ),
    subheading:
      "We email a 1-tab sample sheet today (damage report form, photo-trail compatible) and the full pack the moment it ships. Pre-order is $17 today, $39 at launch — full refund if we miss 2026-05-18.",
    buttonLabel: "Send me the sample",
    successCopy: "✓ Sample on its way",
  },
};

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) return {};

  return {
    title: `${post.title} — OEFR Digital Blog`,
    description: post.description,
    keywords: post.keywords,
    authors: [{ name: post.author }],
    openGraph: {
      title: post.title,
      description: post.description,
      url: `https://oefrenterprise.com/blog/${post.slug}`,
      siteName: "OEFR Digital",
      type: "article",
      publishedTime: post.publishedDate,
      authors: [post.author],
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.description,
      creator: "@eustaceorukpe",
    },
    alternates: {
      canonical: `https://oefrenterprise.com/blog/${post.slug}`,
    },
  };
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) notFound();

  const articleSchema = {
    "@type": "Article",
    headline: post.title,
    description: post.description,
    datePublished: post.publishedDate,
    dateModified: post.updatedDate || post.publishedDate,
    author: {
      "@type": "Organization",
      name: post.author,
      url: "https://oefrenterprise.com",
    },
    publisher: {
      "@type": "Organization",
      name: "OEFR Digital",
      url: "https://oefrenterprise.com",
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://oefrenterprise.com/blog/${post.slug}`,
    },
    keywords: post.keywords.join(", "),
  };

  const faqSchema = post.faqs && post.faqs.length > 0
    ? {
        "@type": "FAQPage",
        mainEntity: post.faqs.map((faq) => ({
          "@type": "Question",
          name: faq.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: faq.answer,
          },
        })),
      }
    : null;

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": faqSchema ? [articleSchema, faqSchema] : [articleSchema],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <article className="px-6 sm:px-10 lg:px-16 py-16">
        <div className="mx-auto max-w-3xl">
          <Link href="/blog" className="inline-flex items-center font-[family-name:var(--font-mono)] text-[11px] tracking-[0.18em] uppercase text-[#7a6f5c] hover:text-[#a66a2c] transition-colors mb-10">
            ← Back to Journal
          </Link>

          <header className="mb-12 pb-10 border-b border-[#d8cdb8]">
            <div className="flex flex-wrap items-center gap-3 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.18em] uppercase text-[#7a6f5c] mb-6">
              <span>{post.author}</span>
              <span>·</span>
              <span>{post.publishedDate}</span>
              <span>·</span>
              <span className="text-[#a66a2c]">{post.readingTime}</span>
            </div>
            <h1 className="font-[family-name:var(--font-fraunces)] font-light text-4xl sm:text-5xl lg:text-6xl tracking-[-0.03em] leading-[1.05] text-[#1a1713]">
              {post.title}
            </h1>
          </header>

          <div className="prose-custom" dangerouslySetInnerHTML={{ __html: post.content }} />

          {post.faqs && post.faqs.length > 0 && (
            <section className="mt-16 pt-10 border-t border-[#d8cdb8]">
              <div className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.2em] uppercase text-[#a66a2c] mb-3">
                Frequently asked questions
              </div>
              <h2 className="font-[family-name:var(--font-fraunces)] font-light text-2xl sm:text-3xl text-[#1a1713] mb-8">
                Common questions about {post.title.length > 60 ? "this topic" : post.title.toLowerCase()}
              </h2>
              <div className="space-y-4">
                {post.faqs.map((faq, idx) => (
                  <details
                    key={idx}
                    className="group border border-[#d8cdb8] rounded-[4px] bg-[#f4efe6]/50 open:bg-[#f4efe6]"
                    {...(idx === 0 ? { open: true } : {})}
                  >
                    <summary className="cursor-pointer select-none px-6 py-4 font-[family-name:var(--font-fraunces)] text-lg text-[#1a1713] hover:text-[#a66a2c] transition-colors list-none flex items-center justify-between gap-4">
                      <span>{faq.question}</span>
                      <span className="shrink-0 text-[#a66a2c] text-xl transition-transform group-open:rotate-45">+</span>
                    </summary>
                    <div className="px-6 pb-5 text-[15px] leading-relaxed text-[#3d362c]">
                      {faq.answer}
                    </div>
                  </details>
                ))}
              </div>
            </section>
          )}

          <div className="mt-16 border border-[#d8cdb8] bg-[#f4efe6] rounded-[4px] p-8 md:p-10">
            <NewsletterSignup
              eyebrow={(BLOG_SIGNUP_OVERRIDES[post.slug] ?? DEFAULT_BLOG_SIGNUP).eyebrow}
              heading={(BLOG_SIGNUP_OVERRIDES[post.slug] ?? DEFAULT_BLOG_SIGNUP).heading}
              subheading={(BLOG_SIGNUP_OVERRIDES[post.slug] ?? DEFAULT_BLOG_SIGNUP).subheading}
              buttonLabel={(BLOG_SIGNUP_OVERRIDES[post.slug] ?? DEFAULT_BLOG_SIGNUP).buttonLabel}
              successCopy={(BLOG_SIGNUP_OVERRIDES[post.slug] ?? DEFAULT_BLOG_SIGNUP).successCopy}
              source={`blog-${post.slug}`}
            />
          </div>

          <div className="mt-12 border border-[#d8cdb8] bg-[#ece3cf] rounded-[4px] p-8 md:p-10">
            <div className="flex flex-col sm:flex-row items-start gap-6">
              <div className="flex-1">
                <div className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.2em] uppercase text-[#a66a2c] mb-2">
                  Recommended product
                </div>
                <p className="font-[family-name:var(--font-fraunces)] text-2xl text-[#1a1713] mb-2">{post.cta.text}</p>
                {post.cta.discount && (
                  <p className="text-sm text-[#3d362c]">
                    Use code{" "}
                    <span className="font-[family-name:var(--font-mono)] font-medium bg-[#f4efe6] border border-[#d8cdb8] px-2 py-0.5 rounded">
                      {post.cta.discount}
                    </span>{" "}
                    for 50% off — limited to first 50 buyers
                  </p>
                )}
              </div>
              <a
                href={post.cta.href}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 inline-flex items-center gap-2 bg-[#1a1713] text-[#f4efe6] px-6 py-3 rounded-full text-sm font-medium hover:bg-[#a66a2c] transition-colors"
              >
                Get it now <span className="font-serif text-lg">→</span>
              </a>
            </div>
          </div>

          <div className="mt-16">
            <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.22em] uppercase text-[#7a6f5c] mb-6">
              Related products
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {post.relatedProducts.map((product) => (
                <a
                  key={product.href}
                  href={product.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="border border-[#d8cdb8] bg-[#ece3cf]/50 rounded-[4px] p-5 hover:border-[#a66a2c] hover:bg-[#ece3cf] transition-colors group"
                >
                  <h3 className="font-[family-name:var(--font-fraunces)] text-lg text-[#1a1713] group-hover:text-[#a66a2c] transition-colors mb-1">
                    {product.name}
                  </h3>
                  <p className="text-xs text-[#7a6f5c]">{product.description}</p>
                </a>
              ))}
            </div>
          </div>

          <div className="mt-16 pt-8 border-t border-[#d8cdb8]">
            <Link href="/blog" className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.18em] uppercase text-[#7a6f5c] hover:text-[#a66a2c] transition-colors">
              ← Back to all posts
            </Link>
          </div>
        </div>
      </article>
    </>
  );
}
