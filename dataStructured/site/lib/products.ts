import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import type { Product, ProductSpec, LaunchReport } from "./types";

const DEFAULT_STATE_DIR = path.join(
  process.cwd(),
  "..",
  "state",
  "products"
);

export async function listProducts(stateDir = DEFAULT_STATE_DIR): Promise<Product[]> {
  let entries;
  try {
    entries = await readdir(stateDir, { withFileTypes: true });
  } catch {
    return [];
  }

  const products: Product[] = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const product = await loadProduct(entry.name, stateDir);
    if (product) products.push(product);
  }

  products.sort((a, b) => b.spec.created.localeCompare(a.spec.created));
  return products;
}

export async function getProduct(
  slug: string,
  stateDir = DEFAULT_STATE_DIR
): Promise<Product | null> {
  return loadProduct(slug, stateDir);
}

async function loadProduct(
  slug: string,
  stateDir: string
): Promise<Product | null> {
  const specPath = path.join(stateDir, slug, "spec.json");
  const launchPath = path.join(stateDir, slug, "launch-report.json");

  let spec: ProductSpec;
  let launch: LaunchReport;
  try {
    spec = JSON.parse(await readFile(specPath, "utf8"));
    launch = JSON.parse(await readFile(launchPath, "utf8"));
  } catch {
    return null;
  }

  if (launch.status !== "FULLY_SHIPPED") return null;
  if (spec.compliance_verdict !== "PASS") return null;

  return { slug, spec, launch };
}
