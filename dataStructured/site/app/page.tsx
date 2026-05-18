import { listProducts } from "@/lib/products";
import { ProductCard } from "@/components/ProductCard";

export default async function HomePage() {
  const products = await listProducts();

  return (
    <div>
      <section className="mb-16">
        <h1 className="text-4xl font-bold tracking-tight">
          Public data, structured for sale.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-neutral-600">
          Niche-specific datasets, drawn from public sources, source-cited on
          every row. Built and shipped by an autonomous agent collective.
        </p>
      </section>

      <section>
        <h2 className="mb-6 text-xl font-semibold">Products</h2>
        {products.length === 0 ? (
          <p className="text-neutral-600">No products shipped yet.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((product) => (
              <ProductCard key={product.slug} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
