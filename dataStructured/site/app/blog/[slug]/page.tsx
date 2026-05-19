import { notFound } from "next/navigation";
import type { Metadata } from "next";
import ReactMarkdown from "react-markdown";
import { getBlogPost, listBlogPosts } from "@/lib/blog";

export async function generateStaticParams() {
  const posts = await listBlogPosts();
  return posts.map((p) => ({ slug: p.frontmatter.slug }));
}

export async function generateMetadata({
  params
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const post = await getBlogPost(params.slug);
  if (!post) return { title: "Not found" };
  return {
    title: post.frontmatter.title,
    description: post.frontmatter.description
  };
}

export default async function BlogPostPage({
  params
}: {
  params: { slug: string };
}) {
  const post = await getBlogPost(params.slug);
  if (!post) notFound();
  return (
    <article className="max-w-3xl">
      <header className="mb-8">
        <p className="text-sm text-neutral-500">
          {new Date(post.frontmatter.published_at).toLocaleDateString()}
        </p>
        <h1 className="text-4xl font-bold tracking-tight mt-2">
          {post.frontmatter.title}
        </h1>
      </header>
      <div className="prose prose-neutral max-w-none">
        <ReactMarkdown>{post.contentMarkdown}</ReactMarkdown>
      </div>
      <hr className="my-12 border-neutral-200" />
      <p className="text-neutral-700">
        Featured product:{" "}
        <a
          href={`/products/${post.frontmatter.product_slug}`}
          className="underline"
        >
          {post.frontmatter.product_slug}
        </a>
      </p>
    </article>
  );
}
