import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Thank you — SSDI Hearing Evidence Letter Kit | OEFR Digital",
  description: "Your SSDI 5-Day INFORM Letter Kit download is ready. 1 letter template, 1 procedural explainer, 1 deadline calendar.",
  robots: { index: false, follow: false },
};

// Gated download endpoint — verifies the Stripe session server-side before
// streaming the PDF (which lives outside public/ so it can't be hotlinked).
const DOWNLOAD_ENDPOINT = "/api/downloads/ssdi-inform-letter";

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
    console.warn("[thank-you/ssdi-5day-inform-letter] STRIPE_SECRET_KEY missing — session not verified");
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
    console.error("[thank-you/ssdi-5day-inform-letter] verify failed:", err);
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
        <p className="text-sm text-[#888] mt-2">
          Haven&apos;t purchased yet?{" "}
          <Link
            className="underline text-[#0a2540]"
            href="/ssdi-hearing-evidence-letter"
          >
            View the SSDI Hearing Evidence Letter Kit
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <p className="text-sm uppercase tracking-widest text-[#00875a] font-semibold mb-3">
        Order confirmed
      </p>
      <h1 className="text-4xl font-bold text-[#0a2540] mb-3">
        Your SSDI Hearing Evidence Letter Kit is ready.
      </h1>
      <p className="text-lg text-[#4a4a4a] mb-8 leading-relaxed">
        Thank you for your purchase. The full kit is below — instant download, 9 pages,
        ready to customize and send before your hearing deadline.
      </p>

      <a
        href={`${DOWNLOAD_ENDPOINT}?session_id=${encodeURIComponent(params.session_id ?? "")}`}
        download="SSDI-5-Day-INFORM-Letter-Kit.pdf"
        className="inline-flex items-center gap-3 bg-[#0a2540] text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-[#163559] transition-colors mb-3"
      >
        <span>&darr; Download the Letter Kit (PDF)</span>
      </a>
      <p className="text-sm text-[#666] mb-12">
        9 pages. Every procedural claim cites the specific federal regulation
        (20 CFR &sect; 404.935(a), HALLEX I-2-5-13, SSR 17-4p).
      </p>

      <div className="border-t border-[#d0d7de] pt-8 mt-8">
        <h2 className="text-xl font-bold text-[#0a2540] mb-3">What&apos;s in the kit</h2>
        <ol className="list-decimal pl-6 text-[#4a4a4a] space-y-1.5 mb-8">
          <li><strong>5-Day INFORM Letter Template (1 page)</strong> — Fill in your name, hearing date, case number, and provider details. Cites 20 CFR &sect; 404.935(a) and HALLEX I-2-5-13.</li>
          <li><strong>Procedural Explainer (5 pages)</strong> — The INFORM vs. SUBMIT asymmetry explained in plain language. Includes SSDI appeal timeline, when to use and not use the letter, delivery methods, and verbatim HALLEX citations.</li>
          <li><strong>60-Day Deadline Calendar Worksheet</strong> — Calculate your INFORM deadline, track provider record requests, monitor evidence status.</li>
          <li><strong>Provider Tracking Table</strong> — Track records requested, records received, INFORM letters sent per provider.</li>
          <li><strong>Legal Resources Page</strong> — Links to official CFR text, HALLEX procedures, disability rights organizations, contingency-fee attorney search guidance.</li>
        </ol>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3">How to use it</h2>
        <ol className="list-decimal pl-6 text-[#4a4a4a] space-y-1.5 mb-8">
          <li>Open the PDF and go to the INFORM Letter Template (page 1).</li>
          <li>Fill in the bracketed fields: your name, SSN (last 4), hearing date, ALJ name, and each provider with outstanding records.</li>
          <li>Fax or mail the letter to your local hearing office at least 5 business days before the hearing date.</li>
          <li>Keep a copy and note the date sent in the Provider Tracking Table.</li>
        </ol>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3">If the download doesn&apos;t start</h2>
        <p className="text-[#4a4a4a] mb-3">
          Right-click the button above and choose &ldquo;Save link as&hellip;&rdquo;
          Or email{" "}
          <a className="underline text-[#0a2540]" href="mailto:info@oefrenterprise.com">
            info@oefrenterprise.com
          </a>{" "}
          and we&apos;ll send the file as an attachment.
        </p>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3 mt-8">Future revisions</h2>
        <p className="text-[#4a4a4a] mb-3">
          Every purchaser gets future revisions free. We&apos;ll email updates to{" "}
          {result.email ?? "your purchase email"}{" "}
          when v1.1, v1.2, etc. ship.
        </p>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3 mt-8">Important</h2>
        <p className="text-[#4a4a4a] mb-3">
          This kit aggregates publicly available federal regulations and SSA procedural
          guidance. It is not legal advice. For case-specific guidance, consult a disability
          attorney or your state&apos;s Disability Rights organization.
        </p>

        <h2 className="text-xl font-bold text-[#0a2540] mb-3 mt-8">Feedback</h2>
        <p className="text-[#4a4a4a]">
          Found something missing? Found something wrong? Email{" "}
          <a className="underline text-[#0a2540]" href="mailto:info@oefrenterprise.com?subject=SSDI%20Letter%20Kit%20feedback">
            info@oefrenterprise.com
          </a>
          . Buyer feedback shapes future revisions.
        </p>
      </div>

      <div className="mt-16 text-sm text-[#888] text-center">
        <Link href="/" className="underline">Back to OEFR Digital</Link>
      </div>
    </div>
  );
}
