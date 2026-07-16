import ROICalculator from "@/components/ROICalculator";

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
            Run a focused 14-day win-back pilot using contacts your business already has
            permission to reach. You approve the audience, offer, and every message before launch.
          </p>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="mailto:info@oefrenterprise.com?subject=Free%20Reactivation%20Audit"
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
              14-day founding pilot
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
              We scope the audience with you, build the campaign, and report what actually happens.
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
                We review list size, age, permission, and sender setup without taking a contact upload.
                You decide whether the pilot is worth running.
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
                Sent over 14 days through an approved, business-owned sender. You approve every
                message, suppression rule, and opt-out before launch.
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
                Every reply and booking is documented. At the end, you get the actual response,
                booking, and revenue data—including a clear stop-or-scale recommendation.
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
            Start with one narrow buyer type, one approved list, and one measurable offer.
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: "🏋️", label: "Gyms & Fitness Studios", desc: "Former members who lapsed" },
              { icon: "🧘", label: "Pilates & Yoga Studios", desc: "Expired intro offers and class packs" },
              { icon: "🥊", label: "Martial Arts Schools", desc: "Former members and trial inquiries" },
              { icon: "🏋️", label: "Independent Trainers", desc: "Past consultations and clients" },
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

      {/* ── Founding pilot ── */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-slate-900/30">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-8 sm:p-10 backdrop-blur text-center">
            <div className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-3">Founding pilot</div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">We are earning the first case study</h2>
            <p className="text-lg text-slate-300 leading-relaxed">
              No invented testimonials and no promised recovery rate. The first three qualified
              fitness businesses get a tightly scoped pilot, direct founder access, and a complete
              results report in exchange for candid feedback and permission to publish verified outcomes.
            </p>
          </div>
        </div>
      </section>

      {/* ── Pilot terms ── */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.07] p-8 sm:p-10 text-center backdrop-blur">
            <div className="text-4xl mb-4">🛡️</div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
              Pilot Terms
            </h2>
            <p className="text-lg text-slate-300 leading-relaxed max-w-xl mx-auto">
              One approved list, one approved offer, three messages, 14 days, and one results report.
              We do not promise replies or bookings; we promise transparent execution and measurement.
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
            <p className="mt-3 text-slate-400">One small paid test before any recurring engagement.</p>
          </div>

          <div className="mb-8 rounded-xl border border-amber-500/30 bg-amber-500/10 px-5 py-3 text-center">
            <span className="text-amber-400 font-semibold text-sm">
              🔥 Three founding-pilot slots — each is handled directly and measured end to end.
            </span>
          </div>

          <div className="mx-auto max-w-xl">
            <div className="rounded-2xl border border-blue-500/50 bg-blue-900/10 p-8">
              <h3 className="text-xl font-bold text-white mb-2">Founding Reactivation Pilot</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-extrabold text-white">$500</span>
                <span className="text-slate-400 text-sm">one time</span>
              </div>
              <ul className="space-y-3 mb-8">
                {[
                  "Free reactivation audit",
                  "Permission and suppression review",
                  "Custom 3-email sequence",
                  "14-day managed send",
                  "Lead handoff report",
                  "Verified results report",
                  "No recurring contract",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <span className="text-emerald-400 flex-shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href="mailto:info@oefrenterprise.com?subject=Free%20Reactivation%20Audit"
                className="block w-full rounded-xl bg-blue-600 px-6 py-3 text-center text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-xl shadow-blue-600/25"
              >
                Book the Free Audit First →
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
                a: "We segment by age during the audit instead of assuming every old contact should be messaged.",
              },
              {
                q: "Do you guarantee replies or bookings?",
                a: "No. We guarantee the agreed work, transparent reporting, and a stop-or-scale recommendation based on actual results.",
              },
              {
                q: "How long does setup take?",
                a: "5 business days from audit call to first email sent. You approve everything first.",
              },
              {
                q: "Do you send emails or do we?",
                a: "The campaign uses a business-owned, approved sender. You approve the audience, messages, suppression list, and opt-out handling before anything is sent.",
              },
              {
                q: "What about consent and compliance?",
                a: "You confirm the contacts were lawfully collected and may be contacted. We include suppression and opt-out handling, and we will not use purchased or scraped contact lists.",
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
            Let us map one narrow test before you spend another dollar acquiring new leads.
          </p>
          <a
            href="mailto:info@oefrenterprise.com?subject=Free%20Reactivation%20Audit"
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
