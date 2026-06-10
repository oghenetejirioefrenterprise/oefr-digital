"use client";
import { useState, useEffect, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  TouchSensor,
  useDroppable,
} from "@dnd-kit/core";
import { useDraggable } from "@dnd-kit/core";
import {
  getCurrentPlan,
  saveCurrentPlan,
  getCustomRecipes,
  getSavedPlans,
  savePlanAs,
  loadSavedPlan,
  deleteSavedPlan,
  createEmptyWeekPlan,
} from "@/lib/storage";
import { BUILT_IN_RECIPES } from "@/lib/recipes";
import { getDayNutrition } from "@/lib/shopping";
import {
  WeekPlan,
  DAYS,
  MEAL_SLOTS,
  MealSlot,
  PlannedMeal,
  Recipe,
  DietaryTag,
} from "@/lib/types";
import {
  Plus,
  X,
  Clock,
  Flame,
  ChevronDown,
  ChevronUp,
  Save,
  FolderOpen,
  Trash2,
  Printer,
  BarChart3,
  Users,
  Share2,
  Download,
} from "lucide-react";
import { generateMealPlanCard, downloadCanvasAsPng, shareCanvas } from "@/lib/share";

// ——— Draggable meal card ———
function MealCard({
  meal,
  recipe,
  onRemove,
}: {
  meal: PlannedMeal;
  recipe: Recipe;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: meal.id,
    data: { meal, recipe },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`meal-card group relative flex items-start gap-1 bg-navy-800 rounded-lg px-2 py-1.5 cursor-grab active:cursor-grabbing text-xs border border-navy-700 hover:border-lime-500/30 ${
        isDragging ? "opacity-30" : ""
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="text-slate-200 font-medium truncate">{recipe.name}</div>
        <div className="flex items-center gap-2 text-slate-500 mt-0.5">
          <span className="flex items-center gap-0.5">
            <Flame className="w-2.5 h-2.5" />
            {Math.round((recipe.nutrition.calories * meal.servings) / recipe.servings)}
          </span>
          <span className="flex items-center gap-0.5">
            <Users className="w-2.5 h-2.5" />
            {meal.servings}
          </span>
        </div>
      </div>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={onRemove}
        className="shrink-0 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

// ——— Droppable slot ———
function MealSlotCell({
  day,
  slot,
  meals,
  allRecipes,
  onAdd,
  onRemove,
}: {
  day: string;
  slot: MealSlot;
  meals: PlannedMeal[];
  allRecipes: Recipe[];
  onAdd: () => void;
  onRemove: (idx: number) => void;
}) {
  const droppableId = `${day}__${slot}`;
  const { setNodeRef, isOver } = useDroppable({ id: droppableId });

  return (
    <div
      ref={setNodeRef}
      className={`min-h-[80px] rounded-xl p-2 space-y-1 transition-colors border ${
        isOver
          ? "bg-lime-500/5 border-lime-500/40"
          : "bg-navy-900 border-navy-700"
      }`}
    >
      {meals.map((m, idx) => {
        const recipe = allRecipes.find((r) => r.id === m.recipeId);
        if (!recipe) return null;
        return (
          <MealCard
            key={m.id}
            meal={m}
            recipe={recipe}
            onRemove={() => onRemove(idx)}
          />
        );
      })}
      <button
        onClick={onAdd}
        className="w-full flex items-center justify-center gap-1 py-1.5 rounded-lg border border-dashed border-navy-600 text-slate-600 hover:border-lime-500/50 hover:text-lime-400 transition-colors text-xs"
      >
        <Plus className="w-3 h-3" />
        Add meal
      </button>
    </div>
  );
}

// ——— Nutrition bar ———
function NutritionBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-500 w-12 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-navy-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-slate-400 w-10 text-right">{value}g</span>
    </div>
  );
}

// ——— Recipe picker modal ———
function RecipePicker({
  onSelect,
  onClose,
  allRecipes,
  slotLabel,
}: {
  onSelect: (r: Recipe) => void;
  onClose: () => void;
  allRecipes: Recipe[];
  slotLabel: string;
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<DietaryTag | "">("");

  const filtered = allRecipes.filter((r) => {
    const matchTag = !filter || r.tags.includes(filter as DietaryTag);
    const matchSearch =
      !search || r.name.toLowerCase().includes(search.toLowerCase());
    return matchTag && matchSearch;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-navy-900 rounded-2xl border border-navy-700 flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-4 border-b border-navy-700">
          <div>
            <div className="text-white font-semibold">Choose a Recipe</div>
            <div className="text-slate-500 text-xs">{slotLabel}</div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-3 border-b border-navy-700 space-y-2">
          <input
            autoFocus
            type="text"
            placeholder="Search recipes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-navy-800 border border-navy-600 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-lime-500"
          />
          <div className="flex gap-1.5 flex-wrap">
            {(["", "Vegetarian", "Vegan", "Keto", "Gluten-Free", "High-Protein"] as const).map((t) => (
              <button
                key={t || "all"}
                onClick={() => setFilter(t)}
                className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                  filter === t ? "bg-lime-500 text-navy-950" : "bg-navy-700 text-slate-400 hover:text-white"
                }`}
              >
                {t || "All"}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-y-auto divide-y divide-navy-800">
          {filtered.length === 0 && (
            <p className="p-6 text-center text-slate-500 text-sm">No recipes match your search.</p>
          )}
          {filtered.map((r) => (
            <button
              key={r.id}
              onClick={() => onSelect(r)}
              className="w-full flex items-center gap-3 p-3 hover:bg-navy-800 transition-colors text-left"
            >
              <div className="flex-1 min-w-0">
                <div className="text-white text-sm font-medium">{r.name}</div>
                <div className="flex items-center gap-3 mt-0.5 text-slate-500 text-xs">
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{r.prepTime + r.cookTime}m</span>
                  <span className="flex items-center gap-1"><Flame className="w-3 h-3" />{r.nutrition.calories} cal</span>
                  <span className="flex items-center gap-1"><Users className="w-3 h-3" />×{r.servings}</span>
                </div>
                {r.isCustom && (
                  <span className="text-lime-400 text-xs">Custom</span>
                )}
              </div>
              <div className="flex flex-col gap-1 items-end">
                {r.tags.slice(0, 2).map((tag) => (
                  <span key={tag} className="px-1.5 py-0.5 rounded text-xs bg-navy-700 text-slate-400">
                    {tag.replace("-", "\u2011")}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ——— Main Planner ———
export default function PlannerPage() {
  const [plan, setPlan] = useState<WeekPlan>(createEmptyWeekPlan);
  const [customRecipes, setCustomRecipes] = useState<Recipe[]>([]);
  const [modal, setModal] = useState<{ day: string; slot: MealSlot } | null>(null);
  const [showNutrition, setShowNutrition] = useState(true);
  const [showSave, setShowSave] = useState(false);
  const [showLoad, setShowLoad] = useState(false);
  const [planName, setPlanName] = useState("");
  const [savedPlans, setSavedPlans] = useState(getSavedPlans);
  const [dragActive, setDragActive] = useState<PlannedMeal | null>(null);
  const [dragActiveRecipe, setDragActiveRecipe] = useState<Recipe | null>(null);

  const allRecipes = [...BUILT_IN_RECIPES, ...customRecipes];

  useEffect(() => {
    setPlan(getCurrentPlan());
    setCustomRecipes(getCustomRecipes());
  }, []);

  useEffect(() => {
    saveCurrentPlan(plan);
  }, [plan]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } })
  );

  const handleDragStart = (e: DragStartEvent) => {
    const { meal, recipe } = e.active.data.current as { meal: PlannedMeal; recipe: Recipe };
    setDragActive(meal);
    setDragActiveRecipe(recipe);
  };

  const handleDragEnd = (e: DragEndEvent) => {
    setDragActive(null);
    setDragActiveRecipe(null);
    const { over, active } = e;
    if (!over) return;
    const { meal } = active.data.current as { meal: PlannedMeal };
    const [targetDay, targetSlot] = (over.id as string).split("__");

    setPlan((prev) => {
      const next = JSON.parse(JSON.stringify(prev)) as WeekPlan;
      // Find and remove from source
      for (const day of DAYS) {
        for (const slot of MEAL_SLOTS) {
          const idx = next[day][slot].findIndex((m) => m.id === meal.id);
          if (idx !== -1) {
            next[day][slot].splice(idx, 1);
            break;
          }
        }
      }
      // Add to target
      next[targetDay][targetSlot as MealSlot].push(meal);
      return next;
    });
  };

  const addMeal = useCallback(
    (recipe: Recipe) => {
      if (!modal) return;
      const { day, slot } = modal;
      setPlan((prev) => {
        const next = JSON.parse(JSON.stringify(prev)) as WeekPlan;
        next[day][slot].push({
          id: `m_${Date.now()}_${Math.random().toString(36).slice(2)}`,
          recipeId: recipe.id,
          servings: recipe.servings,
        });
        return next;
      });
      setModal(null);
    },
    [modal]
  );

  const removeMeal = (day: string, slot: MealSlot, idx: number) => {
    setPlan((prev) => {
      const next = JSON.parse(JSON.stringify(prev)) as WeekPlan;
      next[day][slot].splice(idx, 1);
      return next;
    });
  };

  const clearPlan = () => {
    if (confirm("Clear the entire week plan?")) {
      const empty = createEmptyWeekPlan();
      setPlan(empty);
    }
  };

  const handleSave = () => {
    if (!planName.trim()) return;
    savePlanAs(planName.trim(), plan);
    setSavedPlans(getSavedPlans());
    setPlanName("");
    setShowSave(false);
  };

  const handleLoad = (id: string) => {
    const loaded = loadSavedPlan(id);
    if (loaded) {
      setPlan(loaded);
      setShowLoad(false);
    }
  };

  const handleDelete = (id: string) => {
    deleteSavedPlan(id);
    setSavedPlans(getSavedPlans());
  };

  const printPlan = () => window.print();

  const [sharing, setSharing] = useState(false);

  const handleShareMealPlan = async (mode: "download" | "share") => {
    setSharing(true);
    try {
      const canvas = generateMealPlanCard(plan, allRecipes);
      if (mode === "share") {
        await shareCanvas(canvas, "My Weekly Meal Plan", "Check out my meal plan! Planned with MealCraft Pro");
      } else {
        downloadCanvasAsPng(canvas, "mealcraft-meal-plan.png");
      }
    } finally {
      setSharing(false);
    }
  };

  const slotColors: Record<MealSlot, string> = {
    Breakfast: "text-amber-400",
    Lunch: "text-green-400",
    Dinner: "text-blue-400",
    Snacks: "text-purple-400",
  };

  return (
    <div>
      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Weekly Meal Planner</h1>
          <p className="text-slate-500 text-sm">Drag meals between slots or click to assign</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setShowNutrition(!showNutrition)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700 transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            {showNutrition ? "Hide" : "Show"} Nutrition
          </button>
          <button
            onClick={() => setShowSave(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            Save Plan
          </button>
          <button
            onClick={() => { setSavedPlans(getSavedPlans()); setShowLoad(true); }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700 transition-colors"
          >
            <FolderOpen className="w-3.5 h-3.5" />
            Load Plan
          </button>
          <button
            onClick={clearPlan}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-red-400 hover:text-red-300 text-xs font-medium border border-navy-700 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
          <button
            onClick={printPlan}
            className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs font-medium border border-navy-700 transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            Print
          </button>
          <button
            onClick={() => handleShareMealPlan("download")}
            disabled={sharing}
            className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-lime-400 text-xs font-medium border border-navy-700 transition-colors disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            {sharing ? "Generating…" : "Download Card"}
          </button>
          <button
            onClick={() => handleShareMealPlan("share")}
            disabled={sharing}
            className="no-print flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-lime-500/10 text-lime-400 hover:bg-lime-500/20 text-xs font-bold border border-lime-500/30 transition-colors disabled:opacity-50"
          >
            <Share2 className="w-3.5 h-3.5" />
            Share Meal Plan
          </button>
        </div>
      </div>

      {/* DnD Planner Grid */}
      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="overflow-x-auto pb-4">
          <div className="min-w-[900px]">
            {/* Header row */}
            <div className="grid grid-cols-[80px_repeat(7,1fr)] gap-2 mb-2">
              <div />
              {DAYS.map((day) => {
                const nut = getDayNutrition(plan[day], allRecipes);
                return (
                  <div key={day} className="text-center">
                    <div className="text-lime-400 font-semibold text-sm py-2 px-1 rounded-lg bg-navy-800">
                      {day.slice(0, 3)}
                    </div>
                    {showNutrition && nut.calories > 0 && (
                      <div className="mt-1 space-y-0.5 px-1">
                        <div className="text-xs text-slate-400 font-medium">{nut.calories} cal</div>
                        <div className="flex gap-0.5">
                          <div className="h-1 rounded-full bg-blue-500" style={{ width: `${Math.min((nut.protein / 150) * 100, 100)}%`, flex: 1 }} title={`P: ${nut.protein}g`} />
                          <div className="h-1 rounded-full bg-amber-500" style={{ width: `${Math.min((nut.carbs / 250) * 100, 100)}%`, flex: 1 }} title={`C: ${nut.carbs}g`} />
                          <div className="h-1 rounded-full bg-red-400" style={{ width: `${Math.min((nut.fat / 80) * 100, 100)}%`, flex: 1 }} title={`F: ${nut.fat}g`} />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Meal rows */}
            {MEAL_SLOTS.map((slot) => (
              <div key={slot} className="grid grid-cols-[80px_repeat(7,1fr)] gap-2 mb-2">
                <div className={`flex items-start justify-end pt-2 pr-2 text-xs font-semibold uppercase tracking-wide ${slotColors[slot]}`}>
                  {slot}
                </div>
                {DAYS.map((day) => (
                  <MealSlotCell
                    key={day + slot}
                    day={day}
                    slot={slot}
                    meals={plan[day]?.[slot] ?? []}
                    allRecipes={allRecipes}
                    onAdd={() => setModal({ day, slot })}
                    onRemove={(idx) => removeMeal(day, slot, idx)}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Nutrition summary per day */}
        {showNutrition && (
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
            {DAYS.map((day) => {
              const nut = getDayNutrition(plan[day], allRecipes);
              if (nut.calories === 0) return null;
              return (
                <div key={day} className="bg-navy-900 rounded-xl border border-navy-700 p-3">
                  <div className="text-sm font-semibold text-white mb-2">{day.slice(0, 3)}</div>
                  <div className="text-xl font-bold text-lime-400 mb-2">{nut.calories}<span className="text-xs text-slate-500 font-normal ml-0.5">cal</span></div>
                  <div className="space-y-1.5">
                    <NutritionBar label="Protein" value={nut.protein} max={150} color="bg-blue-500" />
                    <NutritionBar label="Carbs" value={nut.carbs} max={250} color="bg-amber-500" />
                    <NutritionBar label="Fat" value={nut.fat} max={80} color="bg-red-400" />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <DragOverlay>
          {dragActive && dragActiveRecipe && (
            <div className="drag-overlay bg-navy-800 rounded-lg px-3 py-2 border border-lime-500/40 text-sm text-white shadow-xl">
              {dragActiveRecipe.name}
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {/* Recipe picker modal */}
      {modal && (
        <RecipePicker
          allRecipes={allRecipes}
          slotLabel={`${modal.day} — ${modal.slot}`}
          onSelect={addMeal}
          onClose={() => setModal(null)}
        />
      )}

      {/* Save plan modal */}
      {showSave && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-navy-900 rounded-2xl border border-navy-700 p-6">
            <h3 className="text-white font-bold text-lg mb-4">Save Weekly Plan</h3>
            <input
              autoFocus
              type="text"
              placeholder="Plan name (e.g. Week 1 - Keto)"
              value={planName}
              onChange={(e) => setPlanName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              className="w-full px-3 py-2 rounded-lg bg-navy-800 border border-navy-600 text-white placeholder-slate-500 focus:outline-none focus:border-lime-500 mb-4"
            />
            <div className="flex gap-3">
              <button onClick={() => setShowSave(false)} className="flex-1 py-2 rounded-lg bg-navy-700 text-slate-300 hover:bg-navy-600 text-sm font-medium">Cancel</button>
              <button onClick={handleSave} disabled={!planName.trim()} className="flex-1 py-2 rounded-lg bg-lime-500 text-navy-950 font-bold text-sm hover:bg-lime-400 disabled:opacity-40">Save</button>
            </div>
          </div>
        </div>
      )}

      {/* Load plan modal */}
      {showLoad && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm bg-navy-900 rounded-2xl border border-navy-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-bold text-lg">Saved Plans</h3>
              <button onClick={() => setShowLoad(false)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>
            {savedPlans.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-6">No saved plans yet.</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {savedPlans.map((sp) => (
                  <div key={sp.id} className="flex items-center gap-2 p-3 rounded-xl bg-navy-800 border border-navy-700">
                    <div className="flex-1 min-w-0">
                      <div className="text-white text-sm font-medium truncate">{sp.name}</div>
                      <div className="text-slate-500 text-xs">{new Date(sp.updatedAt).toLocaleDateString()}</div>
                    </div>
                    <button onClick={() => handleLoad(sp.id)} className="px-2 py-1 rounded bg-lime-500/20 text-lime-400 text-xs hover:bg-lime-500/30">Load</button>
                    <button onClick={() => handleDelete(sp.id)} className="text-slate-600 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
