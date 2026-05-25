import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Thank you — SBIR/STTR Federal R&D Award Database | OEFR Digital",
  description: "Your SBIR/STTR Award Database download is ready. 17,664 awards, FY2023-2025, all 11 federal agencies.",
  robots: { index: false, follow: false },
};

const CSV_URL = "/downloads/sbir-sttr-award-recipients/SBIR-STTR-Awards-FY2023-2025.csv";

type SearchParams = { session_id?: string };

async function verifyStripeSession(sessionId: string | undefined): Promise<{
  paid: boolean;
  email?: string | null;
  amount_total?: number | null;
  reason?: string;
}> {
  if (!sessionId) return { paid: false, reason: "missing_session_id" };
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) {
    console.warn("[thank-you/sbir-sttr-awards] STRIPE_SECRET_KEY missing — session not verified");
    return { paid: true, reason: "key_missing_trust_redirect" };
  }
  try {
    const Stripe = (await import("stripe")).default;
    const stripe = new Stripe(stripeKey, {
      apiVersion: "2024-12-18.acacia" as any,
      httpClient: Stripe.createFetchHttpClient(),
    });
    const session = await stripe.checkout.sessions.retrieve(sessionId);
    const isPaid = session.payment_status === "paid" || session.status === "complete";
    return {
      paid: isPaid,
      email: session.customer_details?.email ?? session.customer_email,
      amount_total: session.amount_total,
      reason: isPaid ? "verified_paid" : `payment_status=${session.payment_status}`,
    };
  } catch (err) {
    console.error("[thank-you/sbir-sttr-awards] verify failed:", err);
    return { paid: false, reason: "verify_error" };
  }
}

export default async function ThankYouPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const result = await verifyStripeSession(params.session_id);

  if (!result.paid) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20">
        <h1 className="text-3xl font-bold text-[#1a1713] mb-4">We can&apos;t verify your purchase</h1>
        <p className="text-lg text-[#4a4a4a] mb-6">
          This download page is reached after a successful Stripe checkout.
          If you just paid and landed here, your purchase may still be processing —
          give it 60 seconds and refresh.
        </p>
        <p className="text-base text-[#4a4a4a] mb-2">
          If the issue persists, email{" "}
          <a className="underline text-[#0a2540]" href="mailto:info@oefrenterprise.com">
            info@oefrenterprise.com
          </a>{" "}
          with your Stripe receipt — we&apos;ll send the download link directly.
        </p>
        <p className="text-sm text-[#888] mt-6">Reason: {result.reason}</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <p className="text-sm uppercase tracking-widest text-[#00875a] font-semibold mb-3">
        Order confirmed
      </p>
      <h1 className="text-4xl font-bold text-[#0a2540] mb-3">
        Your SBIR/STTR Award Database is ready.
      </h1>
      <p className="text-lg text-[#4a4a4a] mb-8 leading-relaxed">
        Thank you for your purchase. The full dataset is below — 17,664 awards across
        all 11 federal agencies, FY2023-2025, ready for analysis.
      </p>

      <a
        href={CSV_URL}
        download="SBIR-STTR-Awards-FY2023-2025.csv"
        className="inline-flex items-center gap-3 bg-[#0a2540] text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-[#163559] transition-colors mb-3"
      >
        <span>&darr; Download the Database (CSV, ~36 MB)</span>
      </a>
      <p className="text-sm text-[#666] mb-12">
        17,664 rows. Opens in Excel, Google Sheets, or any data tool.
      </p>

      <div className="border-t border-[#d0d7de] pt-8 mt-8">
        <h2 className="text-xl font-bold text-[#0a2540] mb-3">What&apos;s in the dataset</h2>
        <ul className="list-disc pl-6 text-[#4a4a4a] space-y-1.5 mb-8">
          <li><strong>Company details</strong> — Name, city, state, ZIP</li>
          <li><strong>Award data</strong> — Amount, date, fiscal year, contract/grant number</li>
          <li><strong>Agency info</strong> — Awarding agency (DoD, NIH, NSF, DOE, NASA, USDA, DHS, ED, EPA, HHS, USDT) and component (Army, Air Force, DARPA, NCI, etc.)</li>
          <li><strong>Program phase</strong> — Phase I, Phase II, Phase IIB</li>
          <li><strong>Research details</strong> — Topic code, topic title, technology area, solicitation number</li>
          <li><strong>Project abstracts</strong> — 100-500 word descriptions of each funded project</li>
        </ul>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3">Use cases</h2>
        <ul className="list-disc pl-6 text-[#4a4a4a] space-y-1.5 mb-8">
          <li>Build SBIR subcontractor pipelines for large program bids</li>
          <li>Track deep-tech deal flow for early-stage investments</li>
          <li>Prospect for Phase II consulting engagements</li>
          <li>Benchmark competitor agency award distributions</li>
          <li>Identify teaming partners by technology area</li>
        </ul>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3">Data source</h2>
        <p className="text-[#4a4a4a] mb-3">
          Sourced from the official SBIR.gov bulk data portal (data.sbir.gov). Public federal data,
          cleaned and deduplicated. Business contact information retained per FAR regulation;
          personal PII redacted.
        </p>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3 mt-8">If the download doesn&apos;t start</h2>
        <p className="text-[#4a4a4a] mb-3">
          Right-click the button above and choose &ldquo;Save link as&hellip;&rdquo;
          Or email{" "}
          <a className="underline text-[#0a2540]" href="mailto:info@oefrenterprise.com">
            info@oefrenterprise.com
          </a>{" "}
          and we&apos;ll send the file directly.
        </p>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3 mt-8">Updates</h2>
        <p className="text-[#4a4a4a] mb-3">
          Purchasers receive quarterly data refreshes free. We&apos;ll email updates to{" "}
          {result.email ?? "your purchase email"}{" "}
          as new SBIR/STTR awards are published.
        </p>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3 mt-8">Feedback</h2>
        <p className="text-[#4a4a4a]">
          Need a custom slice? Found a data quality issue? Email{" "}
          <a className="underline text-[#0a2540]" href="mailto:info@oefrenterprise.com?subject=SBIR%20STTR%20Database%20feedback">
            info@oefrenterprise.com
          </a>
          .
        </p>
      </div>

      <div className="mt-16 text-sm text-[#888] text-center">
        <Link href="/" className="underline">Back to OEFR Digital</Link>
      </div>
    </div>
  );
}
