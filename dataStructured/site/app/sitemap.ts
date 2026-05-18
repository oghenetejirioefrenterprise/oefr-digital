import type { MetadataRoute } from "next";
import { listProducts } from "@/lib/products";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const products = await listProducts();
  const base = "https://data.oefrenterprise.com";
  const lastModified = new Date();

  return [
    { url: `${base}/`, lastModified, changeFrequency: "daily", priority: 1.0 },
    { url: `${base}/about`, lastModified, changeFrequency: "yearly", priority: 0.5 },
    ...products.map((product) => ({
      url: `${base}/products/${product.slug}`,
      lastModified: new Date(product.spec.created),
      changeFrequency: "weekly" as const,
      priority: 0.9
    }))
  ];
}
