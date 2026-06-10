"use client";
import { useEffect } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { grantAccess } from "@/lib/storage";
import { CheckCircle, Leaf, ArrowRight } from "lucide-react";
import { Suspense } from "react";

function SuccessContent() {
  const params = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    if (params.get("verified") === "1") {
      grantAccess();
    }
    const timer = setTimeout(() => router.replace("/app"), 4000);
    return () => clearTimeout(timer);
  }, [params, router]);

  return (
    <div className="min-h-screen bg-navy-950 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-10 h-10 text-green-400" />
        </div>
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-lime-500 flex items-center justify-center">
            <Leaf className="w-5 h-5 text-navy-950" />
          </div>
          <span className="font-bold text-xl text-white">MealCraft<span className="text-lime-400">Pro</span></span>
        </div>
        <h1 className="text-3xl font-extrabold text-white mb-3">Welcome to the club! 🎉</h1>
        <p className="text-slate-400 mb-6">
          Your lifetime access has been activated. You&apos;ll be redirected to your planner in a moment...
        </p>
        <Link
          href="/app"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-lime-500 text-navy-950 font-bold hover:bg-lime-400 transition-colors"
        >
          Start Planning <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}

export default function SuccessPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-navy-950" />}>
      <SuccessContent />
    </Suspense>
  );
}
