"use client";

import { useState } from "react";

export default function NewsletterSignup() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setStatus("error");
      return;
    }

    setStatus("loading");

    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "newsletter" }),
      });

      if (res.ok) {
        setStatus("success");
        setEmail("");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="rounded-2xl border border-blue-500/20 bg-gradient-to-br from-blue-900/20 via-[#101c35]/60 to-indigo-900/20 p-8 md:p-12 text-center">
      <div className="mx-auto max-w-xl">
        <div className="mb-2 inline-flex items-center rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
          📬 Stay in the loop
        </div>
        <h3 className="mt-4 text-2xl font-bold text-white">
          New products dropping every month
        </h3>
        <p className="mt-3 text-slate-400">
          Get early access, launch discounts, and occasional engineering insights. No spam — ever.
        </p>

        {status === "success" ? (
          <div className="mt-6 rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-4 text-emerald-400 font-medium">
            ✓ You&apos;re on the list! We&apos;ll be in touch.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 flex flex-col sm:flex-row gap-3">
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (status === "error") setStatus("idle");
              }}
              placeholder="you@example.com"
              className={`flex-1 rounded-xl border px-4 py-3 text-sm bg-[#0a0f1e]/80 text-white placeholder-slate-500 outline-none transition-colors focus:border-blue-500/60 ${
                status === "error"
                  ? "border-red-500/40"
                  : "border-slate-700/60"
              }`}
              required
              disabled={status === "loading"}
            />
            <button
              type="submit"
              disabled={status === "loading"}
              className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-500 transition-colors shadow-lg shadow-blue-600/20 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {status === "loading" ? "Subscribing..." : "Notify Me"}
            </button>
          </form>
        )}
        {status === "error" && (
          <p className="mt-2 text-xs text-red-400">Something went wrong. Please try again.</p>
        )}
      </div>
    </div>
  );
}
