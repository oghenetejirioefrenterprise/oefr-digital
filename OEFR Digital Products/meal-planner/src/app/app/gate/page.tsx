"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { grantAccess } from "@/lib/storage";
import { Lock, Leaf, CheckCircle } from "lucide-react";

export default function GatePage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  // Demo unlock code for testing
  const handleUnlock = () => {
    if (code === "DEMO2025" || code === "MEALCRAFT") {
      grantAccess();
      router.replace("/app");
    } else {
      setError("Invalid access code. Purchase to get your code.");
    }
  };

  const handleDemoPurchase = () => {
    // Simulate purchase for demo
    grantAccess();
    router.replace("/app");
  };

  return (
    <div className="min-h-screen bg-navy-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-lime-500 flex items-center justify-center">
            <Leaf className="w-6 h-6 text-navy-950" />
          </div>
          <span className="font-bold text-2xl text-white">
            MealCraft<span className="text-lime-400">Pro</span>
          </span>
        </div>

        <div className="bg-navy-900 rounded-2xl border border-navy-700 p-8">
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-full bg-lime-500/10 flex items-center justify-center mx-auto mb-4">
              <Lock className="w-7 h-7 text-lime-400" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">Full Access Required</h1>
            <p className="text-slate-400 text-sm">
              Enter your access code after purchase, or get instant access for $27.
            </p>
          </div>

          {/* Access code input */}
          <div className="space-y-3 mb-6">
            <input
              type="text"
              placeholder="Enter access code..."
              value={code}
              onChange={(e) => {
                setCode(e.target.value.toUpperCase());
                setError("");
              }}
              onKeyDown={(e) => e.key === "Enter" && handleUnlock()}
              className="w-full px-4 py-3 rounded-xl bg-navy-800 border border-navy-600 text-white placeholder-slate-500 focus:outline-none focus:border-lime-500 text-center text-lg tracking-widest font-mono"
            />
            {error && <p className="text-red-400 text-sm text-center">{error}</p>}
            <button
              onClick={handleUnlock}
              className="w-full py-3 rounded-xl bg-navy-700 text-white font-semibold hover:bg-navy-600 transition-colors"
            >
              Unlock with Code
            </button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-navy-700" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-navy-900 text-slate-500">or</span>
            </div>
          </div>

          {/* Purchase CTA */}
          <Link
            href="/api/checkout"
            className="block w-full py-4 rounded-xl bg-lime-500 text-navy-950 font-bold text-center text-lg hover:bg-lime-400 transition-colors"
          >
            Get Lifetime Access — $27
          </Link>

          <div className="mt-4 space-y-2">
            {[
              "One-time payment, never expires",
              "30-day money-back guarantee",
              "Instant access after purchase",
            ].map((benefit) => (
              <div key={benefit} className="flex items-center gap-2 text-sm text-slate-400">
                <CheckCircle className="w-4 h-4 text-lime-400 shrink-0" />
                {benefit}
              </div>
            ))}
          </div>

          {/* Demo bypass for testing */}
          <div className="mt-6 pt-4 border-t border-navy-700 text-center">
            <button
              onClick={handleDemoPurchase}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
              [Dev: bypass gate for testing]
            </button>
          </div>
        </div>

        <p className="text-center mt-4 text-slate-500 text-sm">
          Want to try first?{" "}
          <Link href="/demo" className="text-lime-400 hover:underline">
            Try the 3-day demo
          </Link>
        </p>
      </div>
    </div>
  );
}
