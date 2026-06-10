"use client";
import { useState, useEffect } from "react";
import { getCurrentPlan, getCustomRecipes, getShoppingChecked, saveShoppingChecked } from "@/lib/storage";
import { generateShoppingList } from "@/lib/shopping";
import { BUILT_IN_RECIPES } from "@/lib/recipes";
import { ShoppingList, ShoppingItem, IngredientCategory } from "@/lib/types";
import {
  ShoppingCart,
  Printer,
  RefreshCw,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronUp,
  Share2,
  Download,
} from "lucide-react";
import { generateShoppingListCard, downloadCanvasAsPng, shareCanvas } from "@/lib/share";

const CATEGORY_ORDER: IngredientCategory[] = [
  "Produce",
  "Protein",
  "Dairy",
  "Grains",
  "Pantry",
  "Frozen",
  "Beverages",
  "Other",
];

const CATEGORY_COLORS: Record<IngredientCategory, string> = {
  Produce: "text-green-400 bg-green-400/10 border-green-400/20",
  Dairy: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  Protein: "text-red-400 bg-red-400/10 border-red-400/20",
  Grains: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  Pantry: "text-slate-400 bg-slate-400/10 border-slate-400/20",
  Frozen: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  Beverages: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  Other: "text-slate-500 bg-slate-500/10 border-slate-500/20",
};

const CATEGORY_EMOJIS: Record<IngredientCategory, string> = {
  Produce: "🥦",
  Dairy: "🥛",
  Protein: "🥩",
  Grains: "🌾",
  Pantry: "🫙",
  Frozen: "🧊",
  Beverages: "🥤",
  Other: "📦",
};

export default function ShoppingPage() {
  const [list, setList] = useState<ShoppingList>({});
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [hideChecked, setHideChecked] = useState(false);

  const allRecipes = [...BUILT_IN_RECIPES, ...getCustomRecipes()];

  const refresh = () => {
    const plan = getCurrentPlan();
    const customRecipes = getCustomRecipes();
    const generated = generateShoppingList(plan, customRecipes);
    setList(generated);
    setChecked(getShoppingChecked());
    // Initialize quantities from generated
    const q: Record<string, number> = {};
    for (const items of Object.values(generated)) {
      for (const item of items ?? []) {
        const key = `${item.ingredient.name}__${item.ingredient.unit}`;
        q[key] = item.totalAmount;
      }
    }
    setQuantities(q);
  };

  useEffect(() => {
    refresh();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleCheck = (key: string) => {
    const next = { ...checked, [key]: !checked[key] };
    setChecked(next);
    saveShoppingChecked(next);
  };

  const toggleCategory = (cat: string) => {
    setCollapsed((c) => ({ ...c, [cat]: !c[cat] }));
  };

  const checkAll = () => {
    const next: Record<string, boolean> = {};
    for (const items of Object.values(list)) {
      for (const item of items ?? []) {
        const key = `${item.ingredient.name}__${item.ingredient.unit}`;
        next[key] = true;
      }
    }
    setChecked(next);
    saveShoppingChecked(next);
  };

  const uncheckAll = () => {
    setChecked({});
    saveShoppingChecked({});
  };

  const totalItems = Object.values(list).reduce((s, items) => s + (items?.length ?? 0), 0);
  const checkedCount = Object.values(checked).filter(Boolean).length;

  const printList = () => window.print();

  const [sharing, setSharing] = useState(false);

  const handleShareShoppingList = async (mode: "download" | "share") => {
    setSharing(true);
    try {
      const canvas = generateShoppingListCard(list, quantities);
      if (mode === "share") {
        await shareCanvas(canvas, "My Shopping List", "Here's my shopping list! Made with MealCraft Pro");
      } else {
        downloadCanvasAsPng(canvas, "mealcraft-shopping-list.png");
      }
    } finally {
      setSharing(false);
    }
  };

  if (totalItems === 0) {
    return (
      <div className="text-center py-20">
        <ShoppingCart className="w-16 h-16 text-slate-700 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Shopping list is empty</h2>
        <p className="text-slate-500 mb-6">Add meals to your weekly planner to generate a shopping list.</p>
        <a href="/app" className="px-6 py-3 rounded-xl bg-lime-500 text-navy-950 font-bold hover:bg-lime-400 transition-colors">
          Go to Planner
        </a>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Shopping List</h1>
          <p className="text-slate-500 text-sm">
            {checkedCount}/{totalItems} items checked · Generated from your weekly plan
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={refresh}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button
            onClick={() => setHideChecked(!hideChecked)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${hideChecked ? "bg-lime-500/10 border-lime-500/30 text-lime-400" : "bg-navy-800 border-navy-700 text-slate-400 hover:text-white"}`}
          >
            Hide Checked
          </button>
          <button onClick={checkAll} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700">
            <CheckSquare className="w-3.5 h-3.5" /> Check All
          </button>
          <button onClick={uncheckAll} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700">
            <Square className="w-3.5 h-3.5" /> Uncheck All
          </button>
          <button onClick={printList} className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700">
            <Printer className="w-3.5 h-3.5" /> Print
          </button>
          <button
            onClick={() => handleShareShoppingList("download")}
            disabled={sharing}
            className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-lime-400 text-xs font-medium border border-navy-700 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" /> {sharing ? "Generating…" : "Download"}
          </button>
          <button
            onClick={() => handleShareShoppingList("share")}
            disabled={sharing}
            className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-lime-500/10 text-lime-400 hover:bg-lime-500/20 text-xs font-bold border border-lime-500/30 transition-colors disabled:opacity-50"
          >
            <Share2 className="w-3.5 h-3.5" /> Share List
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span>Progress</span>
          <span>{totalItems > 0 ? Math.round((checkedCount / totalItems) * 100) : 0}%</span>
        </div>
        <div className="h-2 bg-navy-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-lime-500 rounded-full transition-all duration-300"
            style={{ width: `${totalItems > 0 ? (checkedCount / totalItems) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Categories */}
      <div className="space-y-4">
        {CATEGORY_ORDER.map((cat) => {
          const items = list[cat];
          if (!items || items.length === 0) return null;

          const visibleItems = hideChecked
            ? items.filter((item) => !checked[`${item.ingredient.name}__${item.ingredient.unit}`])
            : items;

          if (visibleItems.length === 0) return null;

          const catChecked = items.filter((item) => checked[`${item.ingredient.name}__${item.ingredient.unit}`]).length;

          return (
            <div key={cat} className="bg-navy-900 rounded-2xl border border-navy-700 overflow-hidden">
              {/* Category header */}
              <button
                onClick={() => toggleCategory(cat)}
                className="w-full flex items-center gap-3 p-4 hover:bg-navy-800 transition-colors"
              >
                <span className={`px-2 py-1 rounded-lg text-xs font-semibold border ${CATEGORY_COLORS[cat]}`}>
                  {CATEGORY_EMOJIS[cat]} {cat}
                </span>
                <span className="text-slate-500 text-xs">{catChecked}/{items.length}</span>
                <div className="ml-auto">
                  {collapsed[cat] ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronUp className="w-4 h-4 text-slate-500" />}
                </div>
              </button>

              {!collapsed[cat] && (
                <div className="border-t border-navy-700 divide-y divide-navy-800">
                  {visibleItems.map((item) => {
                    const key = `${item.ingredient.name}__${item.ingredient.unit}`;
                    const isChecked = !!checked[key];
                    const qty = quantities[key] ?? item.totalAmount;

                    return (
                      <div
                        key={key}
                        className={`flex items-center gap-3 px-4 py-3 transition-colors ${isChecked ? "opacity-50" : ""}`}
                      >
                        <button
                          onClick={() => toggleCheck(key)}
                          className={`shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                            isChecked ? "bg-lime-500 border-lime-500" : "border-navy-600 hover:border-lime-500"
                          }`}
                        >
                          {isChecked && (
                            <svg className="w-3 h-3 text-navy-950" fill="none" viewBox="0 0 12 12">
                              <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          )}
                        </button>

                        <div className="flex-1 min-w-0">
                          <span className={`text-sm ${isChecked ? "line-through text-slate-500" : "text-white"}`}>
                            {item.ingredient.name}
                          </span>
                          {item.recipes.length > 0 && (
                            <div className="text-xs text-slate-600 truncate">{item.recipes.slice(0, 2).join(", ")}{item.recipes.length > 2 ? "..." : ""}</div>
                          )}
                        </div>

                        {/* Quantity adjuster */}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setQuantities((q) => ({ ...q, [key]: Math.max(0, (q[key] ?? item.totalAmount) - 1) }))}
                            className="w-6 h-6 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs flex items-center justify-center"
                          >−</button>
                          <span className="text-slate-300 text-sm w-16 text-center">
                            {qty} {item.ingredient.unit}
                          </span>
                          <button
                            onClick={() => setQuantities((q) => ({ ...q, [key]: (q[key] ?? item.totalAmount) + 1 }))}
                            className="w-6 h-6 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs flex items-center justify-center"
                          >+</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
