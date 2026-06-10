"use client";
import { useState, useEffect } from "react";
import { BUILT_IN_RECIPES } from "@/lib/recipes";
import { getCustomRecipes, saveCustomRecipe, deleteCustomRecipe } from "@/lib/storage";
import { Recipe, DietaryTag, Ingredient, IngredientCategory } from "@/lib/types";
import {
  Plus,
  X,
  Search,
  Clock,
  Flame,
  Users,
  ChefHat,
  Pencil,
  Trash2,
  BookOpen,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const DIET_TAGS: DietaryTag[] = ["Vegetarian", "Vegan", "Keto", "Gluten-Free", "High-Protein"];
const CATEGORIES: IngredientCategory[] = ["Produce", "Dairy", "Protein", "Grains", "Pantry", "Frozen", "Beverages", "Other"];

function RecipeCard({ recipe, onEdit, onDelete }: { recipe: Recipe; onEdit?: () => void; onDelete?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-navy-900 rounded-2xl border border-navy-700 overflow-hidden hover:border-navy-600 transition-colors">
      {recipe.imageUrl && (
        <div className="h-36 overflow-hidden bg-navy-800">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={recipe.imageUrl} alt={recipe.name} className="w-full h-full object-cover opacity-80" />
        </div>
      )}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-white font-semibold text-sm leading-snug">{recipe.name}</h3>
          {recipe.isCustom && (
            <span className="shrink-0 px-1.5 py-0.5 rounded text-xs bg-lime-500/10 text-lime-400 border border-lime-500/20">Custom</span>
          )}
        </div>
        <p className="text-slate-500 text-xs mb-3 line-clamp-2">{recipe.description}</p>

        <div className="flex items-center gap-3 text-xs text-slate-400 mb-3">
          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{recipe.prepTime + recipe.cookTime}m</span>
          <span className="flex items-center gap-1"><Flame className="w-3 h-3" />{recipe.nutrition.calories} cal</span>
          <span className="flex items-center gap-1"><Users className="w-3 h-3" />×{recipe.servings}</span>
        </div>

        <div className="flex flex-wrap gap-1 mb-3">
          {recipe.tags.map((tag) => (
            <span key={tag} className="px-2 py-0.5 rounded-full text-xs bg-navy-800 text-slate-400 border border-navy-700">
              {tag}
            </span>
          ))}
        </div>

        {/* Nutrition row */}
        <div className="grid grid-cols-4 gap-1 mb-3 text-center">
          {[
            { label: "Cal", value: recipe.nutrition.calories, unit: "" },
            { label: "Protein", value: recipe.nutrition.protein, unit: "g" },
            { label: "Carbs", value: recipe.nutrition.carbs, unit: "g" },
            { label: "Fat", value: recipe.nutrition.fat, unit: "g" },
          ].map((n) => (
            <div key={n.label} className="bg-navy-800 rounded-lg py-1.5">
              <div className="text-lime-400 font-bold text-sm">{n.value}{n.unit}</div>
              <div className="text-slate-500 text-xs">{n.label}</div>
            </div>
          ))}
        </div>

        {/* Expand/collapse */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 mb-2"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Hide" : "Show"} ingredients & steps
        </button>

        {expanded && (
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Ingredients</div>
              <ul className="space-y-0.5">
                {recipe.ingredients.map((ing, i) => (
                  <li key={i} className="flex items-center justify-between text-xs text-slate-400">
                    <span>{ing.name}</span>
                    <span className="text-slate-500">{ing.amount} {ing.unit}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Steps</div>
              <ol className="space-y-1">
                {recipe.steps.map((step, i) => (
                  <li key={i} className="flex gap-2 text-xs text-slate-400">
                    <span className="text-lime-400 font-bold shrink-0">{i + 1}.</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}

        {/* Actions */}
        {recipe.isCustom && (
          <div className="flex gap-2 mt-3 pt-3 border-t border-navy-700">
            <button onClick={onEdit} className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-navy-800 text-slate-400 hover:text-white text-xs border border-navy-700 transition-colors">
              <Pencil className="w-3 h-3" /> Edit
            </button>
            <button onClick={onDelete} className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-navy-800 text-red-400 hover:text-red-300 text-xs border border-navy-700 transition-colors">
              <Trash2 className="w-3 h-3" /> Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ——— Recipe Form ———
const emptyIngredient = (): Ingredient => ({ name: "", amount: 1, unit: "g", category: "Produce" });

function RecipeForm({ initial, onSave, onClose }: {
  initial?: Recipe;
  onSave: (r: Recipe) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<Partial<Recipe>>(
    initial ?? {
      name: "",
      description: "",
      servings: 2,
      prepTime: 10,
      cookTime: 15,
      imageUrl: "",
      tags: [],
      ingredients: [emptyIngredient()],
      steps: [""],
      nutrition: { calories: 0, protein: 0, carbs: 0, fat: 0 },
    }
  );

  const updateNutrition = (field: keyof Recipe["nutrition"], val: number) => {
    setForm((f) => ({ ...f, nutrition: { ...(f.nutrition ?? { calories: 0, protein: 0, carbs: 0, fat: 0 }), [field]: val } }));
  };

  const toggleTag = (tag: DietaryTag) => {
    setForm((f) => {
      const tags = f.tags ?? [];
      return { ...f, tags: tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag] };
    });
  };

  const updateIngredient = (i: number, field: keyof Ingredient, val: string | number) => {
    setForm((f) => {
      const ings = [...(f.ingredients ?? [])];
      ings[i] = { ...ings[i], [field]: val } as Ingredient;
      return { ...f, ingredients: ings };
    });
  };

  const addIngredient = () => setForm((f) => ({ ...f, ingredients: [...(f.ingredients ?? []), emptyIngredient()] }));
  const removeIngredient = (i: number) => setForm((f) => ({ ...f, ingredients: (f.ingredients ?? []).filter((_, idx) => idx !== i) }));

  const updateStep = (i: number, val: string) => {
    setForm((f) => {
      const steps = [...(f.steps ?? [])];
      steps[i] = val;
      return { ...f, steps };
    });
  };
  const addStep = () => setForm((f) => ({ ...f, steps: [...(f.steps ?? []), ""] }));
  const removeStep = (i: number) => setForm((f) => ({ ...f, steps: (f.steps ?? []).filter((_, idx) => idx !== i) }));

  const handleSubmit = () => {
    if (!form.name?.trim()) return alert("Recipe name is required");
    const recipe: Recipe = {
      id: initial?.id ?? `custom_${Date.now()}`,
      name: form.name!.trim(),
      description: form.description ?? "",
      servings: form.servings ?? 2,
      prepTime: form.prepTime ?? 0,
      cookTime: form.cookTime ?? 0,
      imageUrl: form.imageUrl ?? "",
      tags: form.tags ?? [],
      ingredients: (form.ingredients ?? []).filter((i) => i.name.trim()),
      steps: (form.steps ?? []).filter((s) => s.trim()),
      nutrition: form.nutrition ?? { calories: 0, protein: 0, carbs: 0, fat: 0 },
      isCustom: true,
    };
    onSave(recipe);
  };

  const inputCls = "w-full px-3 py-2 rounded-lg bg-navy-800 border border-navy-600 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-lime-500";
  const labelCls = "block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
      <div className="w-full max-w-2xl bg-navy-900 rounded-2xl border border-navy-700 mt-8 mb-8">
        <div className="flex items-center justify-between p-5 border-b border-navy-700">
          <h2 className="text-white font-bold text-lg">{initial ? "Edit" : "New"} Recipe</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-5 space-y-4">
          {/* Basic info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className={labelCls}>Recipe Name *</label>
              <input className={inputCls} placeholder="e.g. Greek Salad" value={form.name ?? ""} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Description</label>
              <input className={inputCls} placeholder="Brief description..." value={form.description ?? ""} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            </div>
            <div>
              <label className={labelCls}>Servings</label>
              <input type="number" className={inputCls} value={form.servings ?? 2} onChange={(e) => setForm((f) => ({ ...f, servings: +e.target.value }))} min={1} />
            </div>
            <div>
              <label className={labelCls}>Image URL (optional)</label>
              <input className={inputCls} placeholder="https://..." value={form.imageUrl ?? ""} onChange={(e) => setForm((f) => ({ ...f, imageUrl: e.target.value }))} />
            </div>
            <div>
              <label className={labelCls}>Prep Time (min)</label>
              <input type="number" className={inputCls} value={form.prepTime ?? 0} onChange={(e) => setForm((f) => ({ ...f, prepTime: +e.target.value }))} min={0} />
            </div>
            <div>
              <label className={labelCls}>Cook Time (min)</label>
              <input type="number" className={inputCls} value={form.cookTime ?? 0} onChange={(e) => setForm((f) => ({ ...f, cookTime: +e.target.value }))} min={0} />
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className={labelCls}>Dietary Tags</label>
            <div className="flex flex-wrap gap-2">
              {DIET_TAGS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${(form.tags ?? []).includes(tag) ? "bg-lime-500 text-navy-950" : "bg-navy-800 text-slate-400 border border-navy-600 hover:border-lime-500/30"}`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Nutrition */}
          <div>
            <label className={labelCls}>Nutrition (per serving)</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {(["calories", "protein", "carbs", "fat"] as const).map((field) => (
                <div key={field}>
                  <label className="text-xs text-slate-500 capitalize block mb-1">{field}{field !== "calories" ? " (g)" : ""}</label>
                  <input type="number" className={inputCls} value={form.nutrition?.[field] ?? 0} onChange={(e) => updateNutrition(field, +e.target.value)} min={0} />
                </div>
              ))}
            </div>
          </div>

          {/* Ingredients */}
          <div>
            <label className={labelCls}>Ingredients</label>
            <div className="space-y-2">
              {(form.ingredients ?? []).map((ing, i) => (
                <div key={i} className="grid grid-cols-[1fr_70px_70px_120px_24px] gap-2 items-center">
                  <input className={inputCls} placeholder="Ingredient name" value={ing.name} onChange={(e) => updateIngredient(i, "name", e.target.value)} />
                  <input type="number" className={inputCls} placeholder="Amount" value={ing.amount} onChange={(e) => updateIngredient(i, "amount", +e.target.value)} min={0} step={0.1} />
                  <input className={inputCls} placeholder="Unit" value={ing.unit} onChange={(e) => updateIngredient(i, "unit", e.target.value)} />
                  <select className={inputCls} value={ing.category} onChange={(e) => updateIngredient(i, "category", e.target.value)}>
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <button onClick={() => removeIngredient(i)} className="text-slate-600 hover:text-red-400"><X className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
            <button onClick={addIngredient} className="mt-2 flex items-center gap-1 text-xs text-lime-400 hover:text-lime-300">
              <Plus className="w-3.5 h-3.5" /> Add ingredient
            </button>
          </div>

          {/* Steps */}
          <div>
            <label className={labelCls}>Steps</label>
            <div className="space-y-2">
              {(form.steps ?? []).map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-lime-400 font-bold text-sm pt-2 w-5 shrink-0">{i + 1}.</span>
                  <textarea
                    className={`${inputCls} resize-none`}
                    rows={2}
                    placeholder={`Step ${i + 1}...`}
                    value={step}
                    onChange={(e) => updateStep(i, e.target.value)}
                  />
                  <button onClick={() => removeStep(i)} className="text-slate-600 hover:text-red-400 pt-2"><X className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
            <button onClick={addStep} className="mt-2 flex items-center gap-1 text-xs text-lime-400 hover:text-lime-300">
              <Plus className="w-3.5 h-3.5" /> Add step
            </button>
          </div>
        </div>

        <div className="flex gap-3 p-5 border-t border-navy-700">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl bg-navy-800 text-slate-300 hover:bg-navy-700 font-medium text-sm">Cancel</button>
          <button onClick={handleSubmit} className="flex-1 py-2.5 rounded-xl bg-lime-500 text-navy-950 font-bold text-sm hover:bg-lime-400">Save Recipe</button>
        </div>
      </div>
    </div>
  );
}

// ——— Main page ———
export default function RecipesPage() {
  const [customRecipes, setCustomRecipes] = useState<Recipe[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<DietaryTag | "">("");
  const [showCustomOnly, setShowCustomOnly] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Recipe | undefined>();

  useEffect(() => {
    setCustomRecipes(getCustomRecipes());
  }, []);

  const allRecipes = [...BUILT_IN_RECIPES, ...customRecipes];
  const filtered = allRecipes.filter((r) => {
    if (showCustomOnly && !r.isCustom) return false;
    if (filter && !r.tags.includes(filter)) return false;
    if (search && !r.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleSave = (recipe: Recipe) => {
    saveCustomRecipe(recipe);
    setCustomRecipes(getCustomRecipes());
    setFormOpen(false);
    setEditTarget(undefined);
  };

  const handleDelete = (id: string) => {
    if (!confirm("Delete this custom recipe?")) return;
    deleteCustomRecipe(id);
    setCustomRecipes(getCustomRecipes());
  };

  const handleEdit = (r: Recipe) => {
    setEditTarget(r);
    setFormOpen(true);
  };

  return (
    <div>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Recipe Library</h1>
          <p className="text-slate-500 text-sm">{allRecipes.length} recipes ({customRecipes.length} custom)</p>
        </div>
        <button
          onClick={() => { setEditTarget(undefined); setFormOpen(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-lime-500 text-navy-950 font-bold text-sm hover:bg-lime-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Recipe
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search recipes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl bg-navy-900 border border-navy-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-lime-500"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {(["", ...DIET_TAGS] as const).map((t) => (
            <button
              key={t || "all"}
              onClick={() => setFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === t ? "bg-lime-500 text-navy-950" : "bg-navy-900 text-slate-400 border border-navy-700 hover:text-white"}`}
            >
              {t || "All"}
            </button>
          ))}
          <button
            onClick={() => setShowCustomOnly(!showCustomOnly)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 border transition-colors ${showCustomOnly ? "bg-lime-500/10 border-lime-500/30 text-lime-400" : "bg-navy-900 border-navy-700 text-slate-400 hover:text-white"}`}
          >
            <ChefHat className="w-3.5 h-3.5" /> Custom Only
          </button>
        </div>
      </div>

      {/* Results */}
      {filtered.length === 0 ? (
        <div className="text-center py-20">
          <BookOpen className="w-12 h-12 text-slate-700 mx-auto mb-3" />
          <p className="text-slate-500">No recipes found.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((r) => (
            <RecipeCard
              key={r.id}
              recipe={r}
              onEdit={() => handleEdit(r)}
              onDelete={() => handleDelete(r.id)}
            />
          ))}
        </div>
      )}

      {formOpen && (
        <RecipeForm
          initial={editTarget}
          onSave={handleSave}
          onClose={() => { setFormOpen(false); setEditTarget(undefined); }}
        />
      )}
    </div>
  );
}
