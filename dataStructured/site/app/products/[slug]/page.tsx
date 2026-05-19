import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProduct, listProducts } from "@/lib/products";
import { CheckoutCTAs } from "@/components/CheckoutCTAs";
import { BonusStack } from "@/components/BonusStack";

export async function generateStaticParams() {
  const products = await listProducts();
  return products.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const product = await getProduct(params.slug);
  if (!product) return { title: "Not found" };
  return {
    title: product.spec.name,
    description: product.spec.summary.slice(0, 155),
    openGraph: {
      title: product.spec.name,
      description: product.spec.summary.slice(0, 155)
    }
  };
}

export default async function ProductPage({
  params
}: {
  params: { slug: string };
}) {
  const product = await getProduct(params.slug);
  if (!product) notFound();

  return (
    <article className="space-y-10">
      <header className="space-y-3">
        <p className="text-sm uppercase tracking-wide text-neutral-500">
          {typeof product.spec.row_count === "number"
            ? `${product.spec.row_count.toLocaleString()} rows · ${product.spec.format.replace(/_/g, " ")}`
            : product.spec.format.replace(/_/g, " ")}
        </p>
        <h1 className="text-4xl font-bold tracking-tight">
          {product.spec.name}
        </h1>
        <p className="max-w-2xl text-lg text-neutral-600">
          {product.spec.summary}
        </p>
      </header>

      <CheckoutCTAs product={product} />

      {product.spec.subscription_note && (
        <p className="text-sm text-neutral-600 italic">
          {product.spec.subscription_note}
        </p>
      )}

      <BonusStack items={product.spec.bonus_stack ?? []} />

      {product.spec.audience && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Who buys this
          </h2>
          <p className="text-base text-neutral-700">{product.spec.audience}</p>
        </section>
      )}

      {product.spec.source && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Data source
          </h2>
          <p className="text-sm text-neutral-700">{product.spec.source}</p>
        </section>
      )}
    </article>
  );
}
