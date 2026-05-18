import path from "node:path";
import { describe, it, expect } from "vitest";
import { listProducts, getProduct } from "./products";

const FIXTURES = path.join(__dirname, "__fixtures__");

describe("listProducts", () => {
  it("returns only shipped + compliance_verdict=PASS products", async () => {
    const products = await listProducts(FIXTURES);
    expect(products.map((p) => p.slug)).toEqual(["passing", "shipped-stripe-only"]);
  });

  it("sorts by spec.created descending", async () => {
    const products = await listProducts(FIXTURES);
    for (let i = 1; i < products.length; i++) {
      expect(products[i - 1].spec.created >= products[i].spec.created).toBe(true);
    }
  });
});

describe("getProduct", () => {
  it("returns a passing product by slug", async () => {
    const product = await getProduct("passing", FIXTURES);
    expect(product).not.toBeNull();
    expect(product!.spec.name).toBe("Passing Product");
    expect(product!.launch.stripe_payment_link_url).toBe(
      "https://example.com/buy/passing"
    );
  });

  it("returns null for a compliance-failing product", async () => {
    const product = await getProduct("failing-compliance", FIXTURES);
    expect(product).toBeNull();
  });

  it("returns null for a draft product", async () => {
    const product = await getProduct("draft", FIXTURES);
    expect(product).toBeNull();
  });

  it("returns null for a nonexistent slug", async () => {
    const product = await getProduct("does-not-exist", FIXTURES);
    expect(product).toBeNull();
  });

  it("returns a STRIPE_ONLY product without gumroad URL", async () => {
    const product = await getProduct("shipped-stripe-only", FIXTURES);
    expect(product).not.toBeNull();
    expect(product!.launch.status).toBe("STRIPE_ONLY");
    expect(product!.launch.gumroad_listing_url).toBeUndefined();
  });
});
