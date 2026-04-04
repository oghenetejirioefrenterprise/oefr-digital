"use client";

import { useState } from "react";
import { products, comingSoonProducts, allCategories, FilterCategory } from "@/lib/products";
import ProductCard from "./ProductCard";
import NewsletterSignup from "./NewsletterSignup";

export default function ProductGrid() {
  const [activeFilter, setActiveFilter] = useState<FilterCategory>("All");

  const filteredProducts =
    activeFilter === "All"
      ? products
      : activeFilter === "Coming Soon"
        ? []
        : products.filter((p) => p.category === activeFilter);

  const showComingSoon = activeFilter === "All" || activeFilter === "Coming Soon";

  return (
    <section id="products" className="py-16 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        {/* Section header */}
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-bold text-white mb-3">
            All Products
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            One-time purchase. No subscriptions. No hidden fees. Just tools that work.
          </p>
        </div>

        {/* Category filter tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {allCategories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveFilter(cat)}
              className={`rounded-full px-5 py-2 text-sm font-medium transition-all duration-200 ${
                activeFilter === cat
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/25"
                  : "bg-slate-800/60 text-slate-400 hover:bg-slate-700/60 hover:text-slate-300 border border-slate-700/50"
              }`}
            >
              {cat}
              {cat !== "Coming Soon" && cat !== "All" && (
                <span className="ml-1.5 text-xs opacity-60">
                  ({products.filter((p) => p.category === cat).length})
                </span>
              )}
              {cat === "All" && (
                <span className="ml-1.5 text-xs opacity-60">({products.length})</span>
              )}
              {cat === "Coming Soon" && (
                <span className="ml-1.5 text-xs opacity-60">({comingSoonProducts.length})</span>
              )}
            </button>
          ))}
        </div>

        {/* Product grid */}
        {filteredProducts.length > 0 && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-16">
            {filteredProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}

        {/* Coming Soon section */}
        {showComingSoon && (
          <div className="mt-4">
            <div className="mb-8 flex items-center gap-4">
              <div className="flex-1 h-px bg-slate-800/60" />
              <h3 className="text-lg font-semibold text-slate-400 flex items-center gap-2">
                <span className="text-purple-400">◆</span>
                Coming Soon
              </h3>
              <div className="flex-1 h-px bg-slate-800/60" />
            </div>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {comingSoonProducts.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </div>
        )}

        {/* Newsletter */}
        <div className="mt-20">
          <NewsletterSignup />
        </div>
      </div>
    </section>
  );
}
