const included = [
  "Public lead-path audit with screenshots",
  "Repair of up to three agreed capture issues",
  "Mobile call, email, form, and booking-path checks",
  "Submission routing and confirmation-page verification",
  "Before-and-after test report",
  "No recurring contract",
];

const problems = [
  {
    title: "Broken inquiry forms",
    copy: "A visitor completes the form, but the request never reaches the business—or the form is disabled entirely.",
  },
  {
    title: "Dead quote and booking links",
    copy: "High-intent buttons lead to an error, an empty page, or the wrong destination.",
  },
  {
    title: "Mobile contact friction",
    copy: "Tap-to-call, email, or scheduling paths fail on the device customers use most.",
  },
];

export default function LeadRepairPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="relative overflow-hidden px-4 pb-16 pt-24 sm:px-6 lg:px-8">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-0 h-[420px] w-[760px] -translate-x-1/2 rounded-full bg-amber-500/10 blur-3xl" />
        </div>
        <div className="relative mx-auto max-w-4xl text-center">
          <div className="mb-6 inline-flex rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-1.5 text-sm font-semibold text-amber-300">
            Evidence-first website repair for local businesses
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl">
            Stop Losing Inquiries to
            <span className="mt-2 block bg-gradient-to-r from-amber-300 to-orange-400 bg-clip-text text-transparent">
              Broken Forms and Dead CTAs
            </span>
          </h1>
          <p className="mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-slate-300 sm:text-xl">
            We test the exact path a customer takes from your homepage to a submitted request,
            document the leak, and repair the agreed issues in one fixed-scope sprint.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <a
              href="mailto:info@oefrenterprise.com?subject=Free%20Lead%20Leak%20Audit"
              className="w-full rounded-xl bg-amber-400 px-7 py-3.5 font-bold text-slate-950 transition hover:bg-amber-300 sm:w-auto"
            >
              Request the Free Audit →
            </a>
            <span className="text-sm text-slate-400">No admin access needed for the first audit.</span>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-bold">The leaks we look for</h2>
            <p className="mt-3 text-slate-400">Public, testable failures—not a vague marketing score.</p>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {problems.map((problem) => (
              <article key={problem.title} className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
                <div className="mb-4 text-2xl">⚠️</div>
                <h3 className="text-lg font-bold">{problem.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">{problem.copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-slate-900/40 px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-5xl gap-8 md:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="text-sm font-semibold uppercase tracking-wider text-amber-300">One-time repair sprint</div>
            <h2 className="mt-3 text-3xl font-bold">A bounded fix, not an agency retainer</h2>
            <p className="mt-5 max-w-xl leading-relaxed text-slate-300">
              The free audit identifies the issue first. If the repair fits the sprint, we agree on
              the exact scope before payment. You provide site access only after approving the work.
            </p>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-400">
              We do not promise traffic, leads, or revenue. We verify that the repaired customer path
              works as specified. Complex rebuilds, paid media, CRM migrations, and proprietary systems
              that cannot be safely accessed are quoted separately or declined.
            </p>
          </div>
          <div className="rounded-2xl border border-amber-400/40 bg-slate-950 p-7">
            <div className="text-sm font-semibold text-amber-300">Lead-Capture Repair Sprint</div>
            <div className="mt-3 text-4xl font-extrabold">$750</div>
            <div className="mt-1 text-sm text-slate-400">one time · after the free audit</div>
            <ul className="mt-7 space-y-3">
              {included.map((item) => (
                <li key={item} className="flex gap-3 text-sm text-slate-300">
                  <span className="text-emerald-400">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <a
              href="mailto:info@oefrenterprise.com?subject=Free%20Lead%20Leak%20Audit"
              className="mt-8 block rounded-xl bg-amber-400 px-6 py-3 text-center font-bold text-slate-950 transition hover:bg-amber-300"
            >
              Start With the Free Audit →
            </a>
          </div>
        </div>
      </section>

      <section className="px-4 py-16 text-center sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl rounded-2xl border border-slate-700 bg-slate-900/60 p-8">
          <h2 className="text-2xl font-bold">Built for high-value local inquiries</h2>
          <p className="mx-auto mt-4 max-w-2xl leading-relaxed text-slate-400">
            Home-service contractors, restoration firms, independent professional services, and other
            businesses where one missed request can be worth more than the repair.
          </p>
        </div>
      </section>
    </main>
  );
}
