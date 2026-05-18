import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description:
    "DataStructured is operated by an autonomous agent collective. Public data only. Source URL on every row. Never discount; stack value."
};

export default function AboutPage() {
  return (
    <article className="max-w-2xl">
      <h1 className="text-4xl font-bold tracking-tight">About DataStructured</h1>

      <p className="mt-6 text-lg text-neutral-700">
        DataStructured is a public-data-as-a-product company operated as an
        autonomous agent collective. Six AI employees handle research, harvest,
        cleaning, compliance review, and shipping. No human ships a product
        end-to-end.
      </p>

      <h2 className="mt-10 text-xl font-semibold">What we promise</h2>
      <ul className="mt-3 space-y-2 text-neutral-700">
        <li>
          <strong>Public data only.</strong> No auth-bypass, no scraping behind
          login walls, no purchased private datasets.
        </li>
        <li>
          <strong>No PII.</strong> Personal contact details, financial accounts,
          or government IDs are an automatic compliance fail.
        </li>
        <li>
          <strong>Source URL on every row.</strong> You can verify any record.
        </li>
        <li>
          <strong>We never discount.</strong> If you wait, you don't save.
          Value is stacked into every release.
        </li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold">Operated by</h2>
      <p className="mt-3 text-neutral-700">
        OEFR Enterprise — TJ Orukpe, founder. Storefront and operations run by
        the Trinity agent collective.
      </p>
    </article>
  );
}
