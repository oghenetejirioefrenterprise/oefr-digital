"use client";
import { useState, useCallback } from "react";
import Link from "next/link";
import { BUILT_IN_RECIPES } from "@/lib/recipes";
import { Recipe, MealSlot, PlannedMeal, DietaryTag } from "@/lib/types";
import { Leaf, Lock, ChevronRight, X, Plus, Clock, Flame, Users } from "lucide-react";

const DEMO_DAYS = ["Monday", "Tuesday", "Wednesday"];
const MEAL_SLOTS: MealSlot[] = ["Breakfast", "Lunch", "Dinner", "Snacks"];

type DemoPlan = {
  [day: string]: { [slot in MealSlot]?: PlannedMeal[] };
};

export default function DemoPage() {
  const [plan, setPlan] = useState<DemoPlan>(() => {
    const p: DemoPlan = {};
    for (const d of DEMO_DAYS) {
      p[d] = { Breakfast: [], Lunch: [], Dinner: [], Snacks: [] };
    }
    return p;
  });
  const [modal, setModal] = useState<{ day: string; slot: MealSlot } | null>(null);
  const [filter, setFilter] = useState<DietaryTag | "">("");
  const [search, setSearch] = useState("");

  const filteredRecipes = BUILT_IN_RECIPES.filter((r) => {
    const matchTag = !filter || r.tags.includes(filter);
    const matchSearch = !search || r.name.toLowerCase().includes(search.toLowerCase());
    return matchTag && matchSearch;
  });

  const addMeal = useCallback(
    (recipe: Recipe) => {
      if (!modal) return;
      setPlan((prev) => {
        const next = { ...prev };
        const slot = next[modal.day][modal.slot] ?? [];
        next[modal.day] = {
          ...next[modal.day],
          [modal.slot]: [
            ...slot,
            { id: `${Date.now()}`, recipeId: recipe.id, servings: recipe.servings },
          ],
        };
        return next;
      });
      setModal(null);
    },
    [modal]
  );

  const removeMeal = (day: string, slot: MealSlot, idx: number) => {
    setPlan((prev) => {
      const next = { ...prev };
      const meals = [...(next[day][slot] ?? [])];
      meals.splice(idx, 1);
      next[day] = { ...next[day], [slot]: meals };
      return next;
    });
  };

  const getRecipe = (id: string) => BUILT_IN_RECIPES.find((r) => r.id === id);

  return (
    <div className="min-h-screen bg-navy-950">
      {/* Header */}
      <div className="bg-navy-900 border-b border-navy-800 px-4 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-lime-500 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-navy-950" />
            </div>
            <span className="font-bold text-white">MealCraft<span className="text-lime-400">Pro</span></span>
            <span className="ml-2 px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
              DEMO — 3 days only
            </span>
          </div>
          <Link
            href="/api/checkout"
            className="flex items-center gap-1 px-4 py-2 rounded-lg bg-lime-500 text-navy-950 text-sm font-bold hover:bg-lime-400 transition-colors"
          >
            Unlock Full Version <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-1">3-Day Demo Planner</h1>
          <p className="text-slate-400 text-sm">
            Click any slot to assign a meal. Full version unlocks all 7 days + shopping list + nutrition + more.
          </p>
        </div>

        {/* Planner grid */}
        <div className="overflow-x-auto">
          <div className="grid grid-cols-[100px_1fr_1fr_1fr] gap-3 min-w-[700px]">
            {/* Header row */}
            <div />
            {DEMO_DAYS.map((day) => (
              <div key={day} className="text-center py-2 rounded-lg bg-navy-800 text-lime-400 font-semibold text-sm">
                {day}
              </div>
            ))}

            {/* Meal rows */}
            {MEAL_SLOTS.map((slot) => (
              <>
                <div
                  key={slot + "-label"}
                  className="flex items-start pt-3 justify-end pr-3 text-slate-500 text-xs font-semibold uppercase tracking-wider"
                >
                  {slot}
                </div>
                {DEMO_DAYS.map((day) => {
                  const meals = plan[day][slot] ?? [];
                  return (
                    <div
                      key={day + slot}
                      className="min-h-[90px] rounded-xl bg-navy-900 border border-navy-700 p-2 space-y-1"
                    >
                      {meals.map((m, idx) => {
                        const r = getRecipe(m.recipeId);
                        if (!r) return null;
                        return (
                          <div
                            key={m.id}
                            className="flex items-center justify-between bg-navy-800 rounded-lg px-2 py-1.5 text-xs group"
                          >
                            <span className="text-slate-200 truncate">{r.name}</span>
                            <button
                              onClick={() => removeMeal(day, slot, idx)}
                              className="ml-1 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        );
                      })}
                      <button
                        onClick={() => setModal({ day, slot })}
                        className="w-full flex items-center justify-center gap-1 py-1 rounded-lg border border-dashed border-navy-600 text-slate-600 hover:border-lime-500/50 hover:text-lime-500 transition-colors text-xs"
                      >
                        <Plus className="w-3 h-3" /> Add
                      </button>
                    </div>
                  );
                })}
              </>
            ))}
          </div>
        </div>

        {/* Upsell banner */}
        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-r from-navy-800 to-navy-900 border border-lime-500/20">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Lock className="w-10 h-10 text-lime-400 shrink-0" />
            <div className="flex-1 text-center sm:text-left">
              <h3 className="text-white font-bold text-lg">Unlock the full 7-day planner</h3>
              <p className="text-slate-400 text-sm">
                Get all 7 days, shopping list, nutrition tracking, custom recipes, and saved plans. One-time $27.
              </p>
            </div>
            <Link
              href="/api/checkout"
              className="shrink-0 px-6 py-3 rounded-xl bg-lime-500 text-navy-950 font-bold hover:bg-lime-400 transition-colors whitespace-nowrap"
            >
              Get Full Access — $27
            </Link>
          </div>
        </div>
      </div>

      {/* Recipe picker modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-navy-900 rounded-2xl border border-navy-700 flex flex-col max-h-[80vh]">
            <div className="flex items-center justify-between p-4 border-b border-navy-700">
              <div>
                <div className="text-white font-semibold">Add {modal.slot}</div>
                <div className="text-slate-500 text-xs">{modal.day}</div>
              </div>
              <button onClick={() => setModal(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-3 border-b border-navy-700">
              <input
                type="text"
                placeholder="Search recipes..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-navy-800 border border-navy-600 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-lime-500"
              />
              <div className="flex gap-2 flex-wrap">
                {(["", "Vegetarian", "Vegan", "Keto", "Gluten-Free", "High-Protein"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setFilter(t)}
                    className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                      filter === t
                        ? "bg-lime-500 text-navy-950"
                        : "bg-navy-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    {t || "All"}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-y-auto p-2 space-y-1">
              {filteredRecipes.map((r) => (
                <button
                  key={r.id}
                  onClick={() => addMeal(r)}
                  className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-navy-800 transition-colors text-left"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-white text-sm font-medium truncate">{r.name}</div>
                    <div className="flex items-center gap-3 mt-0.5 text-slate-500 text-xs">
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{r.prepTime + r.cookTime}m</span>
                      <span className="flex items-center gap-1"><Flame className="w-3 h-3" />{r.nutrition.calories} cal</span>
                      <span className="flex items-center gap-1"><Users className="w-3 h-3" />serves {r.servings}</span>
                    </div>
                  </div>
                  <div className="flex gap-1 flex-wrap max-w-[100px]">
                    {r.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className="px-1.5 py-0.5 rounded text-xs bg-navy-700 text-lime-400">{tag.slice(0, 4)}</span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
