import ROICalculator from "@/components/ROICalculator";

const STRIPE_SETUP_LINK =
  process.env.NEXT_PUBLIC_STRIPE_REACTIVATION_SETUP_LINK ||
  "https://buy.stripe.com/6oU3co7P19j1dHd2mG7IY01";
const STRIPE_MONTHLY_LINK =
  process.env.NEXT_PUBLIC_STRIPE_REACTIVATION_MONTHLY_LINK ||
  "https://buy.stripe.com/28E3co0mzan5cD9e5o7IY02";

export default function ReactivationPage() {
  return (
    <>
      {/* ── Hero ── */}
      <section className="relative overflow-hidden pt-20 pb-16 px-4 sm:px-6 lg:px-8">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[500px] rounded-full bg-blue-600/10 blur-3xl" />
          <div className="absolute top-20 left-1/4 w-[300px] h-[300px] rounded-full bg-indigo-600/[0.08] blur-3xl" />
          <div className="absolute top-20 right-1/4 w-[300px] h-[300px] rounded-full bg-cyan-600/[0.06] blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-4xl text-center">
          {/* Eyebrow */}
          <div className="mb-6 inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400">
            <span className="mr-2">💰</span>
            Done-for-you email reactivation · No ads needed
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15] mb-6">
            Recover Revenue
            <br />
            <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-indigo-400 bg-clip-text text-transparent">
              Hiding in Your CRM
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-10">
            We reactivate your cold contacts and put money back in your business.
            No new ads. No new leads. Just results from what you already have.
          </p>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="https://cal.com/oefr-digital/reactivation-audit"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto rounded-xl bg-blue-600 px-8 py-3.5 text-base font-semibold text-white hover:bg-blue-500 transition-all duration-200 shadow-xl shadow-blue-600/25 hover:shadow-blue-500/35"
            >
              Book Free Audit Call →
            </a>
          </div>

          {/* Trust */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="text-emerald-400">✓</span>
              No new ads required
            </span>
            <span className="text-slate-700">|</span>
            <span className="flex items-center gap-1.5">
              <span className="text-blue-400">⚡</span>
              Results in 2 weeks
            </span>
            <span className="text-slate-700">|</span>
            <span className="flex items-center gap-1.5">
              <span className="text-cyan-400">🎯</span>
              Fully managed for you
            </span>
          </div>
        </div>
      </section>

      {/* ── ROI Calculator ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <ROICalculator />
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-12">
            <div className="inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400 mb-4">
              🔄 The Process
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white">How It Works</h2>
            <p className="mt-3 text-slate-400 max-w-xl mx-auto">
              We do all the heavy lifting. You just receive warm leads ready to close.
            </p>
          </div>

          <div className="grid sm:grid-cols-3 gap-6">
            {/* Step 1 */}
            <div className="relative rounded-2xl border border-slate-700/60 bg-slate-900/60 p-7 backdrop-blur">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/30 text-2xl">
                🔍
              </div>
              <div className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">Step 1</div>
              <h3 className="text-lg font-bold text-white mb-3">Free Audit</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                We analyze your cold contacts — who they are, when they went cold, and which segments
                have the highest recovery potential. Zero commitment.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative rounded-2xl border border-slate-700/60 bg-slate-900/60 p-7 backdrop-blur">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/30 text-2xl">
                ✉️
              </div>
              <div className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">Step 2</div>
              <h3 className="text-lg font-bold text-white mb-3">We Build & Run the Sequence</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                We write a personalized 3-email sequence tailored to your business and audience.
                Sent over 2 weeks — fully managed, nothing required from you.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative rounded-2xl border border-slate-700/60 bg-slate-900/60 p-7 backdrop-blur">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-2xl">
                🎯
              </div>
              <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">Step 3</div>
              <h3 className="text-lg font-bold text-white mb-3">You Get Warm Leads</h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Every interested reply gets handed off to you as a ready-to-close lead. You focus on
                closing — we handle everything else.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Who It's For ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-slate-900/30">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400 mb-4">
            🏢 Who It&apos;s For
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Built for Businesses With a Dormant List</h2>
          <p className="text-slate-400 max-w-xl mx-auto mb-10">
            If you have 500+ cold contacts sitting in your CRM doing nothing, you&apos;re losing money every day.
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: "🏋️", label: "Gyms & Fitness Studios", desc: "Former members who lapsed" },
              { icon: "🦷", label: "Dental Clinics", desc: "Patients overdue for visits" },
              { icon: "📊", label: "Coaches & Consultants", desc: "Leads who went cold" },
              { icon: "🏢", label: "Any Service Business", desc: "With 500+ contacts" },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-xl border border-slate-700/60 bg-slate-900/60 p-5 text-center"
              >
                <div className="text-3xl mb-3">{item.icon}</div>
                <div className="text-sm font-semibold text-white mb-1">{item.label}</div>
                <div className="text-xs text-slate-500">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── What's Included ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-12">
            <div className="inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400 mb-4">
              📦 What&apos;s Included
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white">Everything You Need to Win Back Clients</h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: "🔍", title: "Free Reactivation Audit", desc: "Segment analysis before we start — no commitment." },
              { icon: "✍️", title: "Custom 3-Email Sequence", desc: "Written specifically for your business and audience." },
              { icon: "📅", title: "2-Week Managed Send", desc: "We handle scheduling, deliverability, and sending." },
              { icon: "📋", title: "Lead Handoff Report", desc: "Every warm reply documented and handed off to you." },
              { icon: "📈", title: "30-Day Result Tracking", desc: "Open rates, replies, and revenue recovered — tracked." },
              { icon: "💬", title: "Dedicated Support", desc: "Direct access to your campaign manager." },
            ].map((item) => (
              <div
                key={item.title}
                className="flex items-start gap-4 rounded-xl border border-slate-700/60 bg-slate-900/60 p-5"
              >
                <div className="flex-shrink-0 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/20 border border-blue-500/20 text-xl">
                  {item.icon}
                </div>
                <div>
                  <div className="text-sm font-semibold text-white mb-1">{item.title}</div>
                  <div className="text-xs text-slate-400 leading-relaxed">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonial ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-slate-900/30">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-8 sm:p-10 backdrop-blur text-center">
            <div className="text-4xl mb-6">⭐⭐⭐⭐⭐</div>
            <blockquote className="text-lg sm:text-xl text-slate-300 leading-relaxed italic mb-6">
              &ldquo;We had 800+ former members in our CRM who hadn&apos;t visited in over a year. OEFR ran a
              3-email sequence and we got 19 people back in the door inside two weeks. That&apos;s over
              $22,000 in recovered revenue from contacts we&apos;d completely written off. Genuinely shocked
              at how well it worked.&rdquo;
            </blockquote>
            <div className="flex items-center justify-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600/30 border border-blue-500/30 text-sm font-bold text-blue-400">
                MR
              </div>
              <div className="text-left">
                <div className="text-sm font-semibold text-white">Marcus Rivera</div>
                <div className="text-xs text-slate-500">Owner, Iron Peak Fitness — Austin, TX</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Guarantee ── */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.07] p-8 sm:p-10 text-center backdrop-blur">
            <div className="text-4xl mb-4">🛡️</div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
              Our Guarantee
            </h2>
            <p className="text-lg text-slate-300 leading-relaxed max-w-xl mx-auto">
              If we run your reactivation sequence and zero people respond in the first 30 days,
              we refund your setup fee. No paperwork, no questions asked.
            </p>
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-12">
            <div className="inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400 mb-4">
              💵 Pricing
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white">Simple, Transparent Pricing</h2>
            <p className="mt-3 text-slate-400">One campaign typically pays for itself many times over.</p>
          </div>

          {/* Scarcity */}
          <div className="mb-8 rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-3 text-center">
            <span className="text-amber-400 font-semibold text-sm">
              🔥 Limited to 5 clients/month — we cap intake to ensure every campaign gets our full attention.
            </span>
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            {/* Plan A */}
            <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-8">
              <h3 className="text-xl font-bold text-white mb-2">Setup + Monthly</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-extrabold text-white">$750</span>
                <span className="text-slate-400 text-sm">setup</span>
              </div>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-2xl font-bold text-blue-400">$300</span>
                <span className="text-slate-400 text-sm">/month ongoing</span>
              </div>
              <ul className="space-y-3 mb-8">
                {[
                  "Free reactivation audit",
                  "Custom 3-email sequence",
                  "2-week managed send",
                  "Lead handoff report",
                  "30-day result tracking",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <span className="text-emerald-400 flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href={STRIPE_SETUP_LINK}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full rounded-xl border border-slate-600 bg-slate-800 px-6 py-3 text-center text-sm font-semibold text-white hover:border-slate-500 hover:text-white transition-colors"
              >
                Get Started — Pay Setup Fee
              </a>
            </div>

            {/* Plan B - All-in */}
            <div className="relative rounded-2xl border border-blue-500/50 bg-blue-900/10 p-8">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-4 py-1 text-xs font-semibold text-white">
                Best Value
              </div>
              <h3 className="text-xl font-bold text-white mb-2">All-In Monthly</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-white">$900</span>
                <span className="text-slate-400 text-sm">/month, everything included</span>
              </div>
              <ul className="space-y-3 mb-8">
                {[
                  "No setup fee",
                  "Custom 3-email sequence",
                  "2-week managed send",
                  "Lead handoff report",
                  "30-day result tracking",
                  "Dedicated campaign manager",
                  "Monthly strategy review",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <span className="text-blue-400 flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href={STRIPE_MONTHLY_LINK}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full rounded-xl bg-blue-600 px-6 py-3 text-center text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-xl shadow-blue-600/25"
              >
                Subscribe Now - $900/mo
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-slate-900/30">
        <div className="mx-auto max-w-3xl">
          <div className="text-center mb-12">
            <div className="inline-flex items-center rounded-full border border-blue-500/25 bg-blue-500/10 px-4 py-1.5 text-sm font-medium text-blue-400 mb-4">
              ❓ FAQ
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white">Frequently Asked Questions</h2>
          </div>

          <div className="space-y-8">
            {[
              {
                q: "What CRM do you need?",
                a: "We work with any list you can export. Mailchimp, HubSpot, Mindbody, spreadsheets. If you have emails, we can work with it.",
              },
              {
                q: "How old can contacts be?",
                a: "Up to 3 years. Sweet spot is 6\u201324 months.",
              },
              {
                q: "What if we don\u2019t get results?",
                a: "Zero responses in 30 days \u2014 we refund the setup fee. No questions asked.",
              },
              {
                q: "How long does setup take?",
                a: "5 business days from audit call to first email sent. You approve everything first.",
              },
              {
                q: "Do you send emails or do we?",
                a: "We handle everything. You get notified when someone responds and is ready to talk.",
              },
              {
                q: "What\u2019s the cancellation policy?",
                a: "Month to month. Cancel anytime with 7 days notice. No contracts.",
              },
            ].map((item) => (
              <div key={item.q}>
                <h3 className="text-base font-bold text-white mb-1">{item.q}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* -- Final CTA -- */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-900/10 to-transparent" />
        </div>
        <div className="relative mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Your Next Client Is Already in Your CRM
          </h2>
          <p className="text-lg text-slate-400 mb-8 max-w-xl mx-auto">
            Stop leaving money on the table. Let us show you exactly how much revenue is sitting
            in your cold contacts — for free.
          </p>
          <a
            href="https://cal.com/oefr-digital/reactivation-audit"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-xl bg-blue-600 px-10 py-4 text-base font-semibold text-white hover:bg-blue-500 transition-all duration-200 shadow-xl shadow-blue-600/30 hover:shadow-blue-500/40"
          >
            Book Your Free Audit Call →
          </a>
          <p className="mt-4 text-sm text-slate-500">No commitment. No credit card. Just clarity.</p>
        </div>
      </section>
    </>
  );
}
