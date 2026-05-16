import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title:
    "IEP & 504 Parent Advocacy Letter Kit — 12 IDEA-Compliant Templates + 3 Meeting-Day Tools | $24 | OEFR Digital",
  description:
    "12 IDEA-compliant letter templates, every one anchored in the specific 34 CFR / 20 USC section that legally compels a district response. Plus 3 meeting-day tools. Instant digital download — $24. No creator persona. No autism-cure ideology. No certification claims. Just the law + aggregation.",
  alternates: { canonical: "https://www.oefrenterprise.com/iep-504-pack" },
  openGraph: {
    title:
      "IEP & 504 Parent Advocacy Letter Kit — 12 IDEA-Compliant Templates ($24)",
    description:
      "Every letter cites the federal regulation that legally compels a district response. 12 templates + 3 meeting-day tools. Instant download.",
    type: "website",
    url: "https://www.oefrenterprise.com/iep-504-pack",
  },
};

const STRIPE_PLINK = "https://buy.stripe.com/fZubIU8T53YHeLh5yS7IY09";

export default function IEP504PackPage() {
  return (
    <main className="bg-[#f4efe6] text-[#1a1713]">
      {/* Hero */}
      <section className="px-6 sm:px-10 lg:px-16 pt-20 lg:pt-24 pb-16 border-b border-[#d8cdb8]">
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-7">
          Parent Advocacy · 12 letters · 3 tools · Federal citations
        </div>
        <h1 className="font-[family-name:var(--font-fraunces)] font-light leading-[0.98] tracking-[-0.03em] text-[44px] sm:text-[64px] lg:text-[88px] max-w-[1100px] m-0 mb-8">
          The IEP &amp; 504 letter kit{" "}
          <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">
            that cites the law back
          </em>
          .
        </h1>
        <p className="text-[19px] lg:text-[21px] leading-[1.5] text-[#3d362c] max-w-[760px] mb-10">
          Twelve IDEA-compliant letter templates. Every one anchored in the
          specific <strong>20 USC / 34 CFR section</strong> that legally compels
          a district response — not courtesy, law. Plus three meeting-day tools.
          Built so a parent can fill in two blanks, send it, and walk into the
          meeting with the federal regulation already on the table.
        </p>

        <div className="flex flex-wrap items-center gap-5 mb-10">
          <a
            href={STRIPE_PLINK}
            className="inline-flex items-center gap-3 px-9 py-5 bg-[#1a1713] text-[#f4efe6] rounded-full text-[16px] font-semibold hover:bg-[#a66a2c] transition-colors"
          >
            Get the kit — $24{" "}
            <span className="font-serif text-xl">→</span>
          </a>
          <span className="text-[14px] text-[#7a6f5c]">
            Instant PDF · Single-purchaser unlimited family use · Free future revisions
          </span>
        </div>

        {/* Trust strip — federal anchors */}
        <div className="font-[family-name:var(--font-mono)] text-[12px] tracking-[0.18em] uppercase text-[#7a6f5c] pt-6 border-t border-[#d8cdb8]">
          Anchored in
        </div>
        <div className="mt-3 flex flex-wrap gap-x-8 gap-y-3 text-[14px] text-[#1a1713]">
          <span>20 USC §1414</span>
          <span>20 USC §1415(b)(3)</span>
          <span>34 CFR §300.301</span>
          <span>34 CFR §300.503</span>
          <span>34 CFR §300.502</span>
          <span>34 CFR §300.106</span>
          <span>34 CFR §300.530(e)</span>
          <span>34 CFR §104.33</span>
          <span>FERPA · 34 CFR Part 99</span>
        </div>
      </section>

      {/* What you actually buy — 12 letters */}
      <section className="px-6 sm:px-10 lg:px-16 py-20 lg:py-24 border-b border-[#d8cdb8]">
        <div className="grid lg:grid-cols-[260px_1fr] gap-10 lg:gap-20">
          <div>
            <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-3">
              What&rsquo;s in the kit
            </div>
            <h2 className="font-[family-name:var(--font-fraunces)] font-light text-[32px] sm:text-[40px] leading-[1.1] tracking-tight m-0">
              12 letters. 3 tools. Every one cites the federal section.
            </h2>
          </div>
          <div>
            <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-4">
              The 12 letter templates
            </p>
            <ol className="list-decimal pl-6 text-[#3d362c] space-y-2 mb-10 text-[16px] leading-[1.55]">
              <li>
                <strong>Initial Evaluation Request</strong> — 34 CFR §300.301 + §300.300
              </li>
              <li>
                <strong>Evaluation-Denial Response (PWN demand)</strong> — 34 CFR §300.503 + 20 USC §1415(b)(3)
              </li>
              <li>
                <strong>Independent Educational Evaluation (IEE) Request</strong> — 34 CFR §300.502
              </li>
              <li>
                <strong>Accommodation / Modification Request</strong> — 34 CFR §300.116 + 34 CFR §104.33
              </li>
              <li>
                <strong>Extended School Year (ESY) Request</strong> — 34 CFR §300.106
              </li>
              <li>
                <strong>State Complaint Letter</strong> — 34 CFR §§300.151–300.153
              </li>
              <li>
                <strong>Mediation Request</strong> — 34 CFR §300.506
              </li>
              <li>
                <strong>Due Process Complaint</strong> — 34 CFR §§300.507–300.508
              </li>
              <li>
                <strong>Records Request (FERPA + IDEA)</strong> — 34 CFR §300.613 + 34 CFR Part 99
              </li>
              <li>
                <strong>IEP Implementation / Compliance Reminder</strong> — 34 CFR §300.323
              </li>
              <li>
                <strong>Manifestation Determination Review Request</strong> — 34 CFR §300.530(e)
              </li>
              <li>
                <strong>Reevaluation / Triennial Review Request</strong> — 34 CFR §300.303
              </li>
            </ol>

            <p className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-4">
              Plus 3 meeting-day tools
            </p>
            <ul className="list-disc pl-6 text-[#3d362c] space-y-2 text-[16px] leading-[1.55]">
              <li>
                <strong>Meeting Prep Worksheet</strong> — anchored in the 34 CFR §300.322 parent-participation right
              </li>
              <li>
                <strong>IDEA Decision Tree</strong> — full escalation path from concern → evaluation → IEE → due process
              </li>
              <li>
                <strong>Goals Tracker</strong> — quarterly progress-monitoring template per §300.320(a)(3)
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Why this isn't just another free template page */}
      <section className="px-6 sm:px-10 lg:px-16 py-20 lg:py-24 border-b border-[#d8cdb8] bg-[#ece4d2]">
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-6">
          Why this kit
        </div>
        <h2 className="font-[family-name:var(--font-fraunces)] font-light text-[32px] sm:text-[44px] leading-[1.1] tracking-tight m-0 mb-10 max-w-[900px]">
          Free templates rarely cite the regulation. That&rsquo;s the difference.
        </h2>

        <div className="grid md:grid-cols-2 gap-10 lg:gap-16 max-w-[1100px] text-[16px] leading-[1.6] text-[#3d362c]">
          <div>
            <p className="font-semibold text-[#1a1713] mb-2 text-[17px]">
              Citation-anchored, not courtesy-anchored
            </p>
            <p>
              A free request letter that says &ldquo;please evaluate my child&rdquo; gives the district
              every reason to delay. A letter that opens with{" "}
              <em>&ldquo;Under 34 CFR §300.301, I am requesting a full and individual initial evaluation&rdquo;</em>{" "}
              forces a specific procedural clock to start ticking.
            </p>
          </div>

          <div>
            <p className="font-semibold text-[#1a1713] mb-2 text-[17px]">
              No creator persona. No autism-cure ideology. Just the law.
            </p>
            <p>
              OEFR Digital is not a face-led advocate. There is no founder story, no
              hourly-rate funnel, no certification claim. The authority is the federal
              regulation itself, aggregated and surfaced in a usable form.
            </p>
          </div>

          <div>
            <p className="font-semibold text-[#1a1713] mb-2 text-[17px]">
              Edits in any text editor
            </p>
            <p>
              The kit is a PDF that opens in Preview, Adobe, or any browser. The letters
              are also reproducible in plain text — copy into Gmail / Word / Google Docs,
              fill in your child&rsquo;s name and the school&rsquo;s name, and send.
            </p>
          </div>

          <div>
            <p className="font-semibold text-[#1a1713] mb-2 text-[17px]">
              Free future revisions for every purchaser
            </p>
            <p>
              When IDEA regulations update, when case law shifts, when a federal court issues
              a clarifying ruling — every purchaser gets the updated kit emailed at no extra
              cost. v1.1, v1.2, v2.0. No subscription. No re-purchase.
            </p>
          </div>
        </div>
      </section>

      {/* Sample citation excerpt */}
      <section className="px-6 sm:px-10 lg:px-16 py-20 lg:py-24 border-b border-[#d8cdb8]">
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-6">
          Sample · Evaluation-Denial Response (PWN demand)
        </div>
        <h2 className="font-[family-name:var(--font-fraunces)] font-light text-[28px] sm:text-[36px] leading-[1.15] tracking-tight m-0 mb-8 max-w-[900px]">
          One excerpt from one letter — verbatim from the kit.
        </h2>

        <div className="max-w-[820px] bg-[#1a1713] text-[#f4efe6] p-8 lg:p-10 rounded-2xl font-[family-name:var(--font-mono)] text-[14px] leading-[1.7]">
          <p className="mb-4 opacity-60 uppercase tracking-[0.15em] text-[11px]">
            [letter 02 / 12 — opens here]
          </p>
          <p className="mb-4">
            Dear [Principal / Director of Special Education],
          </p>
          <p className="mb-4">
            On [date] I requested a full and individual initial evaluation for my child,
            [child&rsquo;s name], under{" "}
            <span className="text-[#e7b87f]">34 CFR §300.301</span>. On [date] the
            district communicated that the evaluation will not proceed.
          </p>
          <p className="mb-4">
            Under <span className="text-[#e7b87f]">34 CFR §300.503</span> and{" "}
            <span className="text-[#e7b87f]">20 USC §1415(b)(3)</span>, when a public
            agency refuses to initiate or change the identification or evaluation of a
            child, the agency must provide written prior notice that includes (1) a
            description of the action refused, (2) an explanation of why the agency
            refused, (3) a description of each evaluation procedure or report the agency
            used as a basis for the refusal, and (4) a statement of the procedural
            safeguards available to me.
          </p>
          <p className="mb-4">
            Please send the written prior notice required under §300.503 within ten (10)
            business days. If the refusal stands, I will exercise my right to an
            Independent Educational Evaluation at public expense under{" "}
            <span className="text-[#e7b87f]">34 CFR §300.502(b)</span>...
          </p>
          <p className="opacity-60 uppercase tracking-[0.15em] text-[11px]">
            [letter continues — full body in the kit]
          </p>
        </div>

        <p className="mt-6 text-[14px] text-[#7a6f5c] max-w-[820px]">
          Every one of the 12 letters opens this way: the specific federal section,
          quoted accurately, with the procedural obligation it triggers stated plainly.
        </p>
      </section>

      {/* Pricing + refund */}
      <section className="px-6 sm:px-10 lg:px-16 py-20 lg:py-24 border-b border-[#d8cdb8]">
        <div className="grid lg:grid-cols-[1fr_360px] gap-12 lg:gap-20 items-start max-w-[1200px]">
          <div>
            <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-4">
              Price · One-time
            </div>
            <div className="font-[family-name:var(--font-fraunces)] font-light text-[80px] sm:text-[120px] leading-none tracking-[-0.03em] mb-6">
              $24
            </div>
            <p className="text-[18px] text-[#3d362c] leading-[1.55] max-w-[640px] mb-8">
              One purchase. Whole family. Every future revision included. No subscription,
              no recurring charge, no add-on tier. Instant PDF download after checkout.
            </p>
            <a
              href={STRIPE_PLINK}
              className="inline-flex items-center gap-3 px-9 py-5 bg-[#1a1713] text-[#f4efe6] rounded-full text-[16px] font-semibold hover:bg-[#a66a2c] transition-colors"
            >
              Get the kit — $24 <span className="font-serif text-xl">→</span>
            </a>
            <p className="mt-5 text-[13px] text-[#7a6f5c]">
              Secure checkout via Stripe · Cards / Apple Pay / Google Pay · No account needed
            </p>
          </div>

          <div className="bg-[#ece4d2] p-7 rounded-2xl text-[15px] leading-[1.6] text-[#3d362c]">
            <p className="font-semibold text-[#1a1713] mb-3 text-[16px]">
              7-day refund policy
            </p>
            <p className="mb-3">
              If the kit isn&rsquo;t what you needed for any reason, email{" "}
              <a className="underline" href="mailto:support@oefrenterprise.com">
                support@oefrenterprise.com
              </a>{" "}
              within 7 days of purchase with your receipt — we&rsquo;ll refund without
              questions.
            </p>
            <p>
              Read the{" "}
              <Link className="underline" href="/refund">
                full refund policy
              </Link>{" "}
              before you buy.
            </p>
          </div>
        </div>
      </section>

      {/* Further reading — pillar + 4 SEO articles */}
      <section className="px-6 sm:px-10 lg:px-16 py-20 lg:py-24 border-b border-[#d8cdb8] bg-[#ece4d2]">
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-6">
          Free reading · Federal citation deep-dives
        </div>
        <h2 className="font-[family-name:var(--font-fraunces)] font-light text-[30px] sm:text-[40px] leading-[1.1] tracking-tight m-0 mb-10 max-w-[900px]">
          Want to understand the mechanism before you buy?
        </h2>

        <ul className="grid md:grid-cols-2 gap-5 max-w-[1100px] text-[15px] leading-[1.55]">
          <li className="bg-[#f4efe6] p-6 rounded-xl border border-[#d8cdb8]">
            <Link
              className="font-semibold text-[#1a1713] hover:text-[#a66a2c] underline-offset-2 hover:underline"
              href="/blog/iep-504-letter-templates-parent-advocacy"
            >
              IEP &amp; 504 letter templates — parent advocacy overview
            </Link>
            <p className="text-[#7a6f5c] mt-2">The pillar guide: when each letter applies, what triggers escalation.</p>
          </li>
          <li className="bg-[#f4efe6] p-6 rounded-xl border border-[#d8cdb8]">
            <Link
              className="font-semibold text-[#1a1713] hover:text-[#a66a2c] underline-offset-2 hover:underline"
              href="/blog/prior-written-notice-34-cfr-300-503-parent-guide"
            >
              Prior Written Notice (34 CFR §300.503): what parents get in writing
            </Link>
            <p className="text-[#7a6f5c] mt-2">The federal mechanism that forces the district to put a refusal in writing.</p>
          </li>
          <li className="bg-[#f4efe6] p-6 rounded-xl border border-[#d8cdb8]">
            <Link
              className="font-semibold text-[#1a1713] hover:text-[#a66a2c] underline-offset-2 hover:underline"
              href="/blog/independent-educational-evaluation-iee-request-34-cfr-300-502"
            >
              How to request an IEE under 34 CFR §300.502
            </Link>
            <p className="text-[#7a6f5c] mt-2">The two-door rule: district pays, or files due process. No third option.</p>
          </li>
          <li className="bg-[#f4efe6] p-6 rounded-xl border border-[#d8cdb8]">
            <Link
              className="font-semibold text-[#1a1713] hover:text-[#a66a2c] underline-offset-2 hover:underline"
              href="/blog/504-plan-vs-iep-federal-law-differences-parents"
            >
              504 Plan vs IEP — the federal law differences
            </Link>
            <p className="text-[#7a6f5c] mt-2">Section 504 / 34 CFR Part 104 vs IDEA / 34 CFR Part 300, side by side.</p>
          </li>
          <li className="bg-[#f4efe6] p-6 rounded-xl border border-[#d8cdb8]">
            <Link
              className="font-semibold text-[#1a1713] hover:text-[#a66a2c] underline-offset-2 hover:underline"
              href="/blog/idea-60-day-evaluation-timeline-34-cfr-300-301"
            >
              The IDEA 60-day evaluation timeline (34 CFR §300.301)
            </Link>
            <p className="text-[#7a6f5c] mt-2">What actually starts the clock — and what stops it. Consent, not request.</p>
          </li>
        </ul>
      </section>

      {/* FAQ */}
      <section className="px-6 sm:px-10 lg:px-16 py-20 lg:py-24 border-b border-[#d8cdb8]">
        <div className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.24em] uppercase text-[#7a6f5c] mb-6">
          FAQ
        </div>
        <h2 className="font-[family-name:var(--font-fraunces)] font-light text-[32px] sm:text-[44px] leading-[1.1] tracking-tight m-0 mb-12 max-w-[900px]">
          What parents ask before buying.
        </h2>

        <div className="grid md:grid-cols-2 gap-x-16 gap-y-10 max-w-[1200px] text-[15px] leading-[1.6] text-[#3d362c]">
          <div>
            <h3 className="font-semibold text-[#1a1713] text-[17px] mb-2">
              Is this legal advice?
            </h3>
            <p>
              No. The kit is educational. It surfaces federal regulations and provides
              templates that cite them. For case-specific guidance, consult a
              special-education attorney or your state&rsquo;s Parent Training and
              Information (PTI) center.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-[#1a1713] text-[17px] mb-2">
              Does it work for both IEP (IDEA) and 504 (Section 504) plans?
            </h3>
            <p>
              Yes. The kit covers both federal frameworks. IDEA letters cite 20 USC §1400+
              and 34 CFR Part 300. Section 504 letters cite 29 USC §794 and 34 CFR Part 104.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-[#1a1713] text-[17px] mb-2">
              Does it cover my state?
            </h3>
            <p>
              The letters anchor in federal regulation, which applies in every state.
              State-specific procedural variations are noted where they matter (e.g.,
              California, Texas, Florida, New York 60-day-timeline variances).
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-[#1a1713] text-[17px] mb-2">
              Can I share it with my spouse or co-parent?
            </h3>
            <p>
              Yes. Single-purchaser unlimited family use. The kit is licensed for one
              family per purchase — no per-seat fees, no per-device DRM.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-[#1a1713] text-[17px] mb-2">
              What format is the delivery?
            </h3>
            <p>
              Instant PDF download after checkout. The letters are also reproducible as
              plain text — copy each one into Gmail, Word, or Google Docs and customize.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-[#1a1713] text-[17px] mb-2">
              Who built this?
            </h3>
            <p>
              OEFR Digital — an autonomous publisher of citation-anchored compliance and
              advocacy resources. No face on the cover. No founder story. The authority is
              the federal regulation itself, aggregated for usable application.
            </p>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-6 sm:px-10 lg:px-16 py-24 lg:py-32 text-center">
        <h2 className="font-[family-name:var(--font-fraunces)] font-light text-[40px] sm:text-[64px] lg:text-[80px] leading-[1.05] tracking-[-0.03em] m-0 mb-8 max-w-[1100px] mx-auto">
          One purchase.{" "}
          <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">
            Twelve federally-anchored letters
          </em>{" "}
          on the table at every meeting.
        </h2>
        <a
          href={STRIPE_PLINK}
          className="inline-flex items-center gap-3 px-10 py-5 bg-[#1a1713] text-[#f4efe6] rounded-full text-[17px] font-semibold hover:bg-[#a66a2c] transition-colors"
        >
          Get the kit — $24 <span className="font-serif text-xl">→</span>
        </a>
        <p className="mt-6 text-[14px] text-[#7a6f5c]">
          Instant PDF · 7-day refund policy · Free future revisions
        </p>
      </section>
    </main>
  );
}
