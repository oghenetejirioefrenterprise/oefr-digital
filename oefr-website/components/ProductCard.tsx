"use client";

import { useState } from "react";
import { Product } from "@/lib/products";

interface ProductCardProps {
  product: Product;
}

const categoryColors: Record<string, string> = {
  "Finance & Productivity": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  "IT & Engineering": "bg-blue-500/10 text-blue-400 border-blue-500/20",
  "Career & Business": "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  "Coming Soon": "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

const badgeColors: Record<string, string> = {
  Popular: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  "Best Seller": "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  Bundle: "bg-cyan-500/15 text-cyan-400 border-cyan-500/25",
  "Top Rated": "bg-pink-500/15 text-pink-400 border-pink-500/25",
  New: "bg-green-500/15 text-green-400 border-green-500/25",
};

export default function ProductCard({ product }: ProductCardProps) {
  const catColor = categoryColors[product.category] ?? "bg-slate-500/10 text-slate-400 border-slate-500/20";
  const isComingSoon = product.comingSoon;

  const [notifyEmail, setNotifyEmail] = useState("");
  const [notifyStatus, setNotifyStatus] = useState<"idle" | "input" | "loading" | "done">("idle");

  const handleNotify = async () => {
    if (notifyStatus === "idle") {
      setNotifyStatus("input");
      return;
    }

    if (notifyStatus === "input" && notifyEmail.includes("@")) {
      setNotifyStatus("loading");
      try {
        await fetch("/api/subscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: notifyEmail,
            source: `notify-${product.name.toLowerCase().replace(/\s+/g, "-")}`,
          }),
        });
        setNotifyStatus("done");
      } catch {
        setNotifyStatus("input");
      }
    }
  };

  return (
    <article className="group relative flex flex-col rounded-2xl border border-slate-800/60 bg-[#101c35]/60 p-6 backdrop-blur-sm transition-all duration-300 hover:border-blue-500/30 hover:shadow-xl hover:shadow-blue-500/5 hover:-translate-y-0.5">
      {/* Badge */}
      {product.badge && !isComingSoon && (
        <div
          className={`absolute -top-2.5 right-4 rounded-full border px-3 py-0.5 text-xs font-semibold ${badgeColors[product.badge] ?? "bg-slate-500/15 text-slate-400 border-slate-500/25"}`}
        >
          {product.badge}
        </div>
      )}

      {isComingSoon && (
        <div className="absolute -top-2.5 right-4 rounded-full border border-purple-500/25 bg-purple-500/15 px-3 py-0.5 text-xs font-semibold text-purple-400">
          Coming Soon
        </div>
      )}

      {/* Header */}
      <div className="mb-4">
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium mb-3 ${catColor}`}
        >
          {product.category}
        </span>

        <h3 className="text-lg font-bold text-white leading-tight mb-2 group-hover:text-blue-300 transition-colors">
          {product.name}
        </h3>

        <p className="text-sm text-slate-400 leading-relaxed line-clamp-3">
          {product.description}
        </p>
      </div>

      {/* Tags */}
      {product.tags.length > 0 && !isComingSoon && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {product.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded-md bg-slate-800/60 px-2 py-0.5 text-xs text-slate-500"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Rating — only show if there are real reviews */}
      {!isComingSoon && product.reviews > 0 && (
        <div className="mb-4 flex items-center gap-2">
          <div className="flex text-yellow-400 text-sm">
            {"★".repeat(product.rating)}
            {"☆".repeat(5 - product.rating)}
          </div>
          <span className="text-xs text-slate-500">({product.reviews} reviews)</span>
        </div>
      )}
      {!isComingSoon && product.reviews === 0 && (
        <div className="mb-4">
          <span className="text-xs text-slate-500">New product</span>
        </div>
      )}

      <div className="flex-1" />

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-slate-800/60">
        {isComingSoon ? (
          <div className="space-y-2">
            {notifyStatus === "done" ? (
              <div className="text-center text-sm text-emerald-400 font-medium py-2">
                ✓ We&apos;ll notify you at launch!
              </div>
            ) : notifyStatus === "input" || notifyStatus === "loading" ? (
              <div className="flex gap-2">
                <input
                  type="email"
                  value={notifyEmail}
                  onChange={(e) => setNotifyEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="flex-1 rounded-lg border border-purple-500/30 bg-[#0a0f1e]/80 px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-purple-500/60"
                  onKeyDown={(e) => e.key === "Enter" && handleNotify()}
                  disabled={notifyStatus === "loading"}
                  autoFocus
                />
                <button
                  onClick={handleNotify}
                  disabled={notifyStatus === "loading" || !notifyEmail.includes("@")}
                  className="rounded-lg bg-purple-600 px-3 py-2 text-sm font-semibold text-white hover:bg-purple-500 transition-colors disabled:opacity-50"
                >
                  {notifyStatus === "loading" ? "..." : "→"}
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-500">Get notified</span>
                <button
                  onClick={handleNotify}
                  className="rounded-lg border border-purple-500/30 bg-purple-500/10 px-4 py-2 text-sm font-semibold text-purple-400 hover:bg-purple-500/20 transition-colors cursor-pointer"
                >
                  Notify me
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-white">${product.price}</span>
              <span className="text-xs text-slate-500">one-time</span>
            </div>
            <a
              href={product.link}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-all duration-200 shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 group-hover:scale-105"
            >
              Buy Now →
            </a>
          </div>
        )}
      </div>
    </article>
  );
}
