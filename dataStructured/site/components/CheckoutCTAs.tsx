import type { Product } from "@/lib/types";

export function CheckoutCTAs({ product }: { product: Product }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <a
        href={product.launch.stripe_payment_link_url}
        className="inline-flex items-center justify-center rounded-md bg-neutral-900 px-6 py-3 text-base font-semibold text-white hover:bg-neutral-700"
      >
        Buy now — ${product.spec.price_usd} via Stripe
      </a>
      {product.launch.gumroad_listing_url && (
        <a
          href={product.launch.gumroad_listing_url}
          className="inline-flex items-center justify-center rounded-md border border-neutral-300 px-6 py-3 text-base font-semibold text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
        >
          Or buy on Gumroad
        </a>
      )}
      {product.launch.stripe_subscription_payment_link_url && (
        <a
          href={product.launch.stripe_subscription_payment_link_url}
          className="inline-flex items-center justify-center rounded-md border border-dashed border-neutral-400 px-6 py-3 text-sm font-medium text-neutral-600 hover:border-neutral-900 hover:text-neutral-900"
        >
          Or subscribe for quarterly refresh
        </a>
      )}
    </div>
  );
}
