"use client";

import { useState } from "react";
import Link from "next/link";
import { products, comingSoonProducts, allCategories, FilterCategory, Product } from "@/lib/products";

const SWATCHES = ["#ead9c2", "#e6c9a8", "#d9b994", "#eadcc2", "#c9a887"];

export default function ProductCatalog() {
  const [activeFilter, setActiveFilter] = useState<FilterCategory>("All");

  const featured = products.filter((p) => p.featured).slice(0, 3);
  const featuredIds = new Set(featured.map((p) => p.id));
  const rest = products.filter((p) => !featuredIds.has(p.id));

  const filtered =
    activeFilter === "All"
      ? rest
      : activeFilter === "Coming Soon"
        ? []
        : rest.filter((p) => p.category === activeFilter);

  const showComingSoon = activeFilter === "All" || activeFilter === "Coming Soon";
  const now = new Date();
  const monthYear = now.toLocaleDateString("en-US", { month: "short", year: "numeric" });

  return (
    <>
      {/* Featured */}
      <section className="px-6 sm:px-10 lg:px-16 py-24 lg:py-32 border-b border-[#d8cdb8]">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8 mb-16">
          <h2 className="font-[family-name:var(--font-fraunces)] font-light text-5xl lg:text-7xl leading-[0.95] tracking-tight max-w-[700px]">
            What we&rsquo;re <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">shipping</em>
            <br />
            this season.
          </h2>
          <div className="font-[family-name:var(--font-mono)] text-xs text-[#7a6f5c] lg:text-right">
            <span className="block font-[family-name:var(--font-fraunces)] text-4xl text-[#1a1713] tracking-tight leading-none mb-2">
              {String(featured.length).padStart(2, "0")}
            </span>
            Editor&rsquo;s picks, {monthYear}
          </div>
        </div>

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {featured.map((p, i) => (
            <FeaturedCard key={p.id} product={p} index={i} />
          ))}
        </div>
      </section>

      {/* Full catalog */}
      <section id="products" className="px-6 sm:px-10 lg:px-16 py-24 lg:py-32 border-b border-[#d8cdb8]">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8 mb-12">
          <h2 className="font-[family-name:var(--font-fraunces)] font-light text-5xl lg:text-7xl leading-[0.95] tracking-tight">
            The full <em className="font-[family-name:var(--font-instrument)] italic font-normal text-[#a66a2c]">catalog</em>.
          </h2>
          <div className="font-[family-name:var(--font-mono)] text-xs text-[#7a6f5c] lg:text-right">
            <span className="block font-[family-name:var(--font-fraunces)] text-4xl text-[#1a1713] tracking-tight leading-none mb-2">
              {products.length}
            </span>
            Products, five categories
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-12">
          {allCategories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveFilter(cat)}
              className={`px-4 py-2 border border-[#1a1713] rounded-full text-[13px] transition-colors ${
                activeFilter === cat ? "bg-[#1a1713] text-[#f4efe6]" : "bg-transparent text-[#1a1713] hover:bg-[#ece3cf]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="border-t border-[#1a1713]">
          {filtered.map((p, i) => (
            <CatalogRow key={p.id} product={p} index={i + featured.length} />
          ))}
          {filtered.length === 0 && activeFilter !== "Coming Soon" && (
            <div className="py-16 text-center font-[family-name:var(--font-mono)] text-xs tracking-[0.18em] uppercase text-[#7a6f5c]">
              No products in this category yet
            </div>
          )}
        </div>

        {showComingSoon && comingSoonProducts.length > 0 && (
          <div className="mt-16">
            <div className="flex items-center gap-6 mb-8">
              <span className="flex-1 h-px bg-[#d8cdb8]" />
              <span className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.22em] uppercase text-[#7a6f5c]">
                Coming Soon
              </span>
              <span className="flex-1 h-px bg-[#d8cdb8]" />
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {comingSoonProducts.map((p) => (
                <div
                  key={p.id}
                  className="border border-dashed border-[#c4b897] rounded p-6 bg-[#ece3cf]/50"
                >
                  <div className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.18em] uppercase text-[#a66a2c] mb-3">
                    In Studio
                  </div>
                  <h3 className="font-[family-name:var(--font-fraunces)] text-2xl mb-3">{p.name}</h3>
                  <p className="text-sm leading-relaxed text-[#3d362c]">{p.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </>
  );
}

function FeaturedCard({ product, index }: { product: Product; index: number }) {
  const swatch = SWATCHES[index % SWATCHES.length];
  return (
    <Link
      href={product.link}
      target={product.link.startsWith("http") ? "_blank" : undefined}
      rel={product.link.startsWith("http") ? "noopener noreferrer" : undefined}
      className="group flex flex-col bg-[#ece3cf] border border-[#d8cdb8] rounded-[4px] overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
    >
      <div
        className="relative aspect-[4/3] border-b border-[#d8cdb8] flex items-end p-6"
        style={{ background: swatch }}
      >
        {product.badge && (
          <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.2em] uppercase text-[#1a1713]/70">
            {product.badge}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-3 p-7 flex-1">
        <div className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.18em] uppercase text-[#a66a2c]">
          {product.category}
        </div>
        <h3 className="font-[family-name:var(--font-fraunces)] font-normal text-3xl leading-tight tracking-tight text-[#1a1713]">
          {product.name}
        </h3>
        <p className="text-sm leading-relaxed text-[#3d362c] flex-1">{product.description}</p>
        <div className="flex items-baseline justify-between pt-4 border-t border-dashed border-[#c4b897]">
          <div className="font-[family-name:var(--font-fraunces)] text-2xl">
            ${product.price}
            <span className="font-[family-name:var(--font-mono)] text-[10px] text-[#7a6f5c] tracking-[0.12em] ml-1 uppercase">
              once
            </span>
          </div>
          <span className="font-serif text-xl text-[#1a1713] group-hover:text-[#a66a2c] group-hover:translate-x-1 transition-all">
            →
          </span>
        </div>
      </div>
    </Link>
  );
}

function CatalogRow({ product, index }: { product: Product; index: number }) {
  return (
    <Link
      href={product.link}
      target={product.link.startsWith("http") ? "_blank" : undefined}
      rel={product.link.startsWith("http") ? "noopener noreferrer" : undefined}
      className="group grid grid-cols-[60px_1fr_100px_80px_40px] md:grid-cols-[80px_1fr_240px_120px_120px_60px] gap-4 md:gap-6 items-center py-6 md:py-7 border-b border-[#d8cdb8] hover:bg-[#ece3cf] hover:-mx-6 hover:px-6 md:hover:-mx-6 md:hover:px-6 transition-[background,margin,padding] duration-150"
    >
      <span className="font-[family-name:var(--font-mono)] text-xs text-[#7a6f5c]">
        {String(index + 1).padStart(3, "0")}
      </span>
      <div>
        <h3 className="font-[family-name:var(--font-fraunces)] text-xl md:text-[26px] leading-tight tracking-tight group-hover:text-[#a66a2c] transition-colors">
          {product.name}
        </h3>
        <p className="md:hidden mt-1 text-xs text-[#3d362c] line-clamp-2">{product.description}</p>
      </div>
      <p className="hidden md:block text-[13px] leading-snug text-[#3d362c] line-clamp-2">
        {product.description}
      </p>
      <span className="hidden md:block font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] uppercase text-[#7a6f5c]">
        {product.category}
      </span>
      <span className="font-[family-name:var(--font-fraunces)] text-xl md:text-[26px] text-right">
        ${product.price}
      </span>
      <span className="font-serif text-lg md:text-xl text-right text-[#1a1713] group-hover:text-[#a66a2c] group-hover:translate-x-1 transition-all">
        →
      </span>
    </Link>
  );
}
