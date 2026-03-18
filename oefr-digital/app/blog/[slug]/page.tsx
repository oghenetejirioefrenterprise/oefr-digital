import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { blogPosts, getPostBySlug, getAllSlugs } from "@/lib/blog-posts";

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

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.description,
    datePublished: post.publishedDate,
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

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <article className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          {/* Back link */}
          <Link
            href="/blog"
            className="inline-flex items-center text-sm text-slate-500 hover:text-blue-400 transition-colors mb-8"
          >
            ← Back to Blog
          </Link>

          {/* Header */}
          <header className="mb-10">
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-4 leading-tight">
              {post.title}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500">
              <span>{post.author}</span>
              <span>·</span>
              <span>{post.publishedDate}</span>
              <span>·</span>
              <span className="inline-flex items-center rounded-full bg-blue-500/10 border border-blue-500/25 px-3 py-0.5 text-xs font-medium text-blue-400">
                {post.readingTime}
              </span>
            </div>
          </header>

          {/* Content */}
          <div
            className="prose-custom"
            dangerouslySetInnerHTML={{ __html: post.content }}
          />

          {/* CTA Box */}
          <div className="mt-12 rounded-2xl border border-blue-800 bg-blue-950/50 p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="flex-1">
                <p className="text-lg font-bold text-white mb-1">
                  {post.cta.text}
                </p>
                {post.cta.discount && (
                  <p className="text-sm text-blue-300">
                    Use code{" "}
                    <span className="font-mono font-bold bg-blue-900/50 px-2 py-0.5 rounded">
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
                className="shrink-0 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-lg shadow-blue-600/25"
              >
                Get It Now →
              </a>
            </div>
          </div>

          {/* Related Products */}
          <div className="mt-16">
            <h2 className="text-xl font-bold text-white mb-6">
              Related Products
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {post.relatedProducts.map((product) => (
                <a
                  key={product.href}
                  href={product.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-blue-500/40 transition-colors group"
                >
                  <h3 className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors mb-1">
                    {product.name}
                  </h3>
                  <p className="text-xs text-slate-500">{product.description}</p>
                </a>
              ))}
            </div>
          </div>

          {/* Back link bottom */}
          <div className="mt-12 pt-8 border-t border-slate-800">
            <Link
              href="/blog"
              className="text-sm text-slate-500 hover:text-blue-400 transition-colors"
            >
              ← Back to all posts
            </Link>
          </div>
        </div>
      </article>
    </>
  );
}
