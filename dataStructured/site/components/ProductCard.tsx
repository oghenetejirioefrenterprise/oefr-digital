import type { Product } from "@/lib/types";

export function ProductCard({ product }: { product: Product }) {
  return (
    <a
      href={`/products/${product.slug}`}
      className="block rounded-lg border border-neutral-200 p-6 transition hover:border-neutral-900 hover:shadow-sm"
    >
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-base font-semibold">{product.spec.name}</h3>
        <span className="text-lg font-semibold tabular-nums">
          ${product.spec.price_usd}
        </span>
      </div>
      <p className="mb-3 line-clamp-3 text-sm text-neutral-600">
        {product.spec.summary}
      </p>
      <div className="flex items-center gap-4 text-xs text-neutral-500">
        <span>{product.spec.row_count.toLocaleString()} rows</span>
        <span>{product.spec.format.replace(/_/g, " ")}</span>
      </div>
    </a>
  );
}
