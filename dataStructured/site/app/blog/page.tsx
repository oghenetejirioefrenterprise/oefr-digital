import type { Metadata } from "next";
import { listBlogPosts } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "How to use DataStructured's public-data products — guides, comparisons, refresh notes."
};

export default async function BlogIndex() {
  const posts = await listBlogPosts();
  return (
    <article className="max-w-3xl">
      <h1 className="text-4xl font-bold tracking-tight">Blog</h1>
      <p className="mt-4 text-lg text-neutral-600">
        Guides, comparisons, and refresh notes for our public-data products.
      </p>
      {posts.length === 0 ? (
        <p className="mt-12 text-neutral-600">No posts yet.</p>
      ) : (
        <ul className="mt-12 space-y-8">
          {posts.map((p) => (
            <li key={p.frontmatter.slug}>
              <a href={`/blog/${p.frontmatter.slug}`} className="block group">
                <h2 className="text-xl font-semibold group-hover:underline">
                  {p.frontmatter.title}
                </h2>
                <p className="mt-1 text-sm text-neutral-500">
                  {new Date(p.frontmatter.published_at).toLocaleDateString()}
                </p>
                <p className="mt-2 text-neutral-700">{p.frontmatter.description}</p>
              </a>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
