import type { MetadataRoute } from "next";
import { listProducts } from "@/lib/products";
import { listBlogPosts } from "@/lib/blog";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [products, posts] = await Promise.all([
    listProducts(),
    listBlogPosts()
  ]);
  const base = "https://data.oefrenterprise.com";
  const lastModified = new Date();

  return [
    { url: `${base}/`, lastModified, changeFrequency: "daily", priority: 1.0 },
    { url: `${base}/about`, lastModified, changeFrequency: "yearly", priority: 0.5 },
    { url: `${base}/blog`, lastModified, changeFrequency: "weekly", priority: 0.8 },
    ...products.map((product) => ({
      url: `${base}/products/${product.slug}`,
      lastModified: new Date(product.spec.created),
      changeFrequency: "weekly" as const,
      priority: 0.9
    })),
    ...posts.map((p) => ({
      url: `${base}/blog/${p.frontmatter.slug}`,
      lastModified: new Date(p.frontmatter.published_at),
      changeFrequency: "monthly" as const,
      priority: 0.7
    }))
  ];
}
