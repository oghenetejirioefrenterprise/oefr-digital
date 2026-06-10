import Link from "next/link";

const FEATURES = [
  { kicker: "01", title: "Weekly meal grid", desc: "Drag-and-drop meals across Mon\u2013Sun with Breakfast, Lunch, Dinner & Snacks slots." },
  { kicker: "02", title: "50+ built-in recipes", desc: "Curated library of healthy recipes with ingredients, servings, prep time, and nutrition." },
  { kicker: "03", title: "Auto shopping list", desc: "Ingredients auto-aggregated by category \u2014 Produce, Dairy, Protein, Grains." },
  { kicker: "04", title: "Daily nutrition overview", desc: "See calories, protein, carbs, and fat per day. Stay on target without counting." },
  { kicker: "05", title: "Dietary filters", desc: "Vegetarian, Vegan, Keto, Gluten-Free, High-Protein. Stick to your lifestyle." },
  { kicker: "06", title: "Print & export", desc: "Print your weekly plan and shopping list with one click. Works on mobile too." },
];

const PRO_FEATURES = [
  "Full weekly planner (Mon\u2013Sun)",
  "50+ curated healthy recipes",
  "Auto shopping list by category",
  "Daily nutrition tracking",
  "Custom recipe builder",
  "Dietary filters (Keto, Vegan\u2026)",
  "Save multiple weekly plans",
  "Print plan & shopping list",
  "All data stays on your device",
  "30-day money-back guarantee",
];

const FAQ = [
  { q: "Is this really a one-time purchase?", a: "Yes. Pay $27 once and own it forever. No monthly fees, no subscriptions, no upsells." },
  { q: "Is my data private?", a: "Completely. All your meal plans, recipes, and shopping lists are stored in your browser. Nothing ever leaves your device." },
  { q: "Can I create my own recipes?", a: "Absolutely. The custom recipe builder lets you add name, ingredients, steps, nutrition facts, and an image." },
  { q: "Does it work on mobile?", a: "Yes. MealCraft Pro is fully mobile-first responsive. Plan from your phone, grocery shop from the app." },
  { q: "What if I want a refund?", a: "30-day no-questions-asked refund. Just email us. But try the demo first." },
  { q: "Can I save multiple weekly plans?", a: "Yes. Save as many weekly plans as you want \u2014 meal prep for different weeks or seasons." },
];

const fraunces = { fontFamily: 'Fraunces, "Times New Roman", serif' };
const instrument = { fontFamily: '"Instrument Serif", serif' };
const mono = { fontFamily: '"JetBrains Mono", ui-monospace, monospace' };

export default function LandingPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#f4efe6", color: "#1a1713" }}>
      {/* Nav */}
      <nav style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 50, background: "rgba(244,239,230,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid #d8cdb8" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "0 24px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link href="/" style={{ display: "flex", alignItems: "baseline", gap: "10px", textDecoration: "none" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "36px", height: "36px", borderRadius: "50%", background: "#1a1713", color: "#f4efe6", fontStyle: "italic", fontSize: "17px", ...fraunces, alignSelf: "center" }}>mc</span>
            <span style={{ fontSize: "22px", letterSpacing: "-0.02em", fontWeight: 500, color: "#1a1713", ...fraunces }}>MealCraft Pro</span>
          </Link>
          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            <a href="#features" style={{ fontSize: "14px", color: "#1a1713", textDecoration: "none" }}>Features</a>
            <a href="#pricing" style={{ fontSize: "14px", color: "#1a1713", textDecoration: "none" }}>Pricing</a>
            <Link href="/demo" style={{ fontSize: "14px", color: "#1a1713", textDecoration: "none" }}>Demo</Link>
            <Link href="/api/checkout" style={{ background: "#1a1713", color: "#f4efe6", fontSize: "14px", fontWeight: 500, padding: "10px 20px", borderRadius: "999px", textDecoration: "none" }}>
              Get access <span style={{ ...fraunces, fontSize: "18px" }}>→</span>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: "128px 24px 96px", borderBottom: "1px solid #d8cdb8" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.24em", textTransform: "uppercase", color: "#7a6f5c", marginBottom: "28px" }}>
            Meal planning · One-time purchase
          </div>
          <h1 style={{ ...fraunces, fontWeight: 300, fontSize: "clamp(3rem, 8vw, 7rem)", letterSpacing: "-0.04em", lineHeight: 0.95, maxWidth: "1200px", margin: "0 0 32px" }}>
            Meal prep, <span style={{ ...instrument, fontStyle: "italic", fontWeight: 400, color: "#a66a2c" }}>simplified</span>.
          </h1>
          <p style={{ fontSize: "clamp(18px, 2vw, 22px)", lineHeight: 1.5, color: "#3d362c", maxWidth: "720px", marginBottom: "48px" }}>
            Drag-and-drop weekly meal plans, auto-generated shopping lists, daily nutrition tracking, and 50+ curated recipes. Pay once, cook forever.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "16px" }}>
            <Link href="/api/checkout" style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "#1a1713", color: "#f4efe6", fontSize: "15px", fontWeight: 500, padding: "16px 32px", borderRadius: "999px", textDecoration: "none" }}>
              Get MealCraft Pro — $27 <span style={{ ...fraunces, fontSize: "20px" }}>→</span>
            </Link>
            <Link href="/demo" style={{ fontSize: "15px", color: "#1a1713", borderBottom: "1px solid #1a1713", paddingBottom: "4px", padding: "16px 24px", textDecoration: "none" }}>
              Try the demo
            </Link>
          </div>
          <p style={{ ...mono, marginTop: "24px", fontSize: "11px", letterSpacing: "0.18em", textTransform: "uppercase", color: "#7a6f5c" }}>
            One-time · Works offline · Mobile-first
          </p>
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{ padding: "96px 24px 128px", borderBottom: "1px solid #d8cdb8" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr", gap: "64px", marginBottom: "64px" }}>
            <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.24em", textTransform: "uppercase", color: "#7a6f5c" }}>Features</div>
            <h2 style={{ ...fraunces, fontWeight: 300, fontSize: "clamp(2.5rem, 5vw, 4.5rem)", letterSpacing: "-0.03em", lineHeight: 0.95, margin: 0 }}>
              Everything you need to <span style={{ ...instrument, fontStyle: "italic", fontWeight: 400, color: "#a66a2c" }}>eat well</span>.
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "48px 40px", borderTop: "1px solid #d8cdb8", paddingTop: "48px" }}>
            {FEATURES.map((f) => (
              <div key={f.title}>
                <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.22em", textTransform: "uppercase", color: "#a66a2c", marginBottom: "12px" }}>{f.kicker}</div>
                <h3 style={{ ...fraunces, fontSize: "24px", color: "#1a1713", marginBottom: "8px" }}>{f.title}</h3>
                <p style={{ fontSize: "14px", color: "#3d362c", lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" style={{ padding: "96px 24px 128px", background: "rgba(236,227,207,0.4)", borderBottom: "1px solid #d8cdb8" }}>
        <div style={{ maxWidth: "640px", margin: "0 auto", textAlign: "center" }}>
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.24em", textTransform: "uppercase", color: "#7a6f5c", marginBottom: "28px" }}>Pricing</div>
          <h2 style={{ ...fraunces, fontWeight: 300, fontSize: "clamp(2.5rem, 5vw, 4rem)", letterSpacing: "-0.03em", lineHeight: 1.05 }}>
            Pay once. <span style={{ ...instrument, fontStyle: "italic", fontWeight: 400, color: "#a66a2c" }}>Cook forever</span>.
          </h2>
          <div style={{ background: "#1a1713", color: "#f4efe6", padding: "48px 40px", borderRadius: "4px", marginTop: "48px", textAlign: "left" }}>
            <div style={{ ...mono, fontSize: "10px", letterSpacing: "0.22em", textTransform: "uppercase", color: "#c9a887", marginBottom: "16px" }}>MealCraft Pro</div>
            <div style={{ ...fraunces, fontWeight: 300, fontSize: "80px", letterSpacing: "-0.03em", lineHeight: 1, marginBottom: "8px", textAlign: "center" }}>$27</div>
            <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.18em", textTransform: "uppercase", color: "#c9a887", textAlign: "center", marginBottom: "32px" }}>
              Once · Lifetime access
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 32px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px" }}>
              {PRO_FEATURES.map((f) => (
                <li key={f} style={{ fontSize: "13px", color: "#e8dcc5", display: "flex", gap: "8px" }}>
                  <span style={{ color: "#c9a887" }}>✦</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <div style={{ textAlign: "center" }}>
              <Link href="/api/checkout" style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "#f4efe6", color: "#1a1713", fontSize: "15px", fontWeight: 500, padding: "14px 32px", borderRadius: "999px", textDecoration: "none" }}>
                Get MealCraft Pro <span style={{ ...fraunces, fontSize: "20px" }}>→</span>
              </Link>
              <p style={{ ...mono, marginTop: "16px", fontSize: "10px", letterSpacing: "0.14em", textTransform: "uppercase", color: "#c9a887" }}>
                30-day refund · Secure Stripe · Instant access
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section style={{ padding: "96px 24px", borderBottom: "1px solid #d8cdb8" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto", display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr", gap: "64px" }}>
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.24em", textTransform: "uppercase", color: "#7a6f5c" }}>FAQ</div>
          <div style={{ maxWidth: "860px" }}>
            <h2 style={{ ...fraunces, fontWeight: 300, fontSize: "clamp(2.5rem, 5vw, 4rem)", letterSpacing: "-0.03em", lineHeight: 1.05, margin: "0 0 32px" }}>
              Frequently asked.
            </h2>
            {FAQ.map((f) => (
              <div key={f.q} style={{ borderTop: "1px solid #d8cdb8", paddingTop: "24px", marginTop: "32px" }}>
                <h3 style={{ ...fraunces, fontSize: "20px", color: "#1a1713", marginBottom: "12px" }}>{f.q}</h3>
                <p style={{ fontSize: "15px", color: "#3d362c", lineHeight: 1.6, margin: 0 }}>{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: "48px 24px", background: "#f4efe6" }}>
        <div style={{ maxWidth: "1280px", margin: "0 auto", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", borderRadius: "50%", background: "#1a1713", color: "#f4efe6", fontStyle: "italic", fontSize: "14px", ...fraunces, alignSelf: "center" }}>mc</span>
            <span style={{ fontSize: "18px", ...fraunces }}>MealCraft Pro</span>
            <span style={{ ...mono, fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase", color: "#7a6f5c" }}>
              Part of <a href="https://www.oefrenterprise.com" style={{ color: "#a66a2c", textDecoration: "none" }}>OEFR Digital</a>
            </span>
          </div>
          <div style={{ ...mono, display: "flex", flexWrap: "wrap", gap: "24px", fontSize: "11px", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7a6f5c" }}>
            <Link href="/demo" style={{ color: "inherit", textDecoration: "none" }}>Demo</Link>
            <Link href="/app" style={{ color: "inherit", textDecoration: "none" }}>App</Link>
            <a href="mailto:oghenetejiri@oefrenterprise.com" style={{ color: "inherit", textDecoration: "none" }}>Contact</a>
            <span>© {new Date().getFullYear()}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
