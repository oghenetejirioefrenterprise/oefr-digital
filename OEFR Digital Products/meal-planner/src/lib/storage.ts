import {
  WeekPlan,
  SavedPlan,
  Recipe,
  UserSettings,
  DEFAULT_SETTINGS,
  DAYS,
  MEAL_SLOTS,
} from "./types";

const KEYS = {
  CURRENT_PLAN: "mp_current_plan",
  SAVED_PLANS: "mp_saved_plans",
  CUSTOM_RECIPES: "mp_custom_recipes",
  SETTINGS: "mp_settings",
  ACCESS_TOKEN: "mp_access",
  SHOPPING_CHECKED: "mp_shopping_checked",
};

function safeGet<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const val = localStorage.getItem(key);
    return val ? (JSON.parse(val) as T) : fallback;
  } catch {
    return fallback;
  }
}

function safeSet(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

export function createEmptyWeekPlan(): WeekPlan {
  const plan: WeekPlan = {};
  for (const day of DAYS) {
    plan[day] = {} as WeekPlan[string];
    for (const slot of MEAL_SLOTS) {
      plan[day][slot] = [];
    }
  }
  return plan;
}

// Current plan
export function getCurrentPlan(): WeekPlan {
  return safeGet<WeekPlan>(KEYS.CURRENT_PLAN, createEmptyWeekPlan());
}

export function saveCurrentPlan(plan: WeekPlan) {
  safeSet(KEYS.CURRENT_PLAN, plan);
}

// Saved plans
export function getSavedPlans(): SavedPlan[] {
  return safeGet<SavedPlan[]>(KEYS.SAVED_PLANS, []);
}

export function savePlanAs(name: string, plan: WeekPlan): SavedPlan {
  const plans = getSavedPlans();
  const newPlan: SavedPlan = {
    id: `plan_${Date.now()}`,
    name,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    plan,
  };
  plans.push(newPlan);
  safeSet(KEYS.SAVED_PLANS, plans);
  return newPlan;
}

export function updateSavedPlan(id: string, plan: WeekPlan) {
  const plans = getSavedPlans();
  const idx = plans.findIndex((p) => p.id === id);
  if (idx >= 0) {
    plans[idx].plan = plan;
    plans[idx].updatedAt = new Date().toISOString();
    safeSet(KEYS.SAVED_PLANS, plans);
  }
}

export function deleteSavedPlan(id: string) {
  const plans = getSavedPlans().filter((p) => p.id !== id);
  safeSet(KEYS.SAVED_PLANS, plans);
}

export function loadSavedPlan(id: string): WeekPlan | null {
  const plans = getSavedPlans();
  return plans.find((p) => p.id === id)?.plan ?? null;
}

// Custom recipes
export function getCustomRecipes(): Recipe[] {
  return safeGet<Recipe[]>(KEYS.CUSTOM_RECIPES, []);
}

export function saveCustomRecipe(recipe: Recipe) {
  const recipes = getCustomRecipes();
  const idx = recipes.findIndex((r) => r.id === recipe.id);
  if (idx >= 0) {
    recipes[idx] = recipe;
  } else {
    recipes.push({ ...recipe, isCustom: true });
  }
  safeSet(KEYS.CUSTOM_RECIPES, recipes);
}

export function deleteCustomRecipe(id: string) {
  const recipes = getCustomRecipes().filter((r) => r.id !== id);
  safeSet(KEYS.CUSTOM_RECIPES, recipes);
}

// Settings
export function getSettings(): UserSettings {
  return safeGet<UserSettings>(KEYS.SETTINGS, DEFAULT_SETTINGS);
}

export function saveSettings(settings: UserSettings) {
  safeSet(KEYS.SETTINGS, settings);
}

// Access gate
export function hasAccess(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(KEYS.ACCESS_TOKEN) === "granted";
}

export function grantAccess() {
  if (typeof window !== "undefined") {
    localStorage.setItem(KEYS.ACCESS_TOKEN, "granted");
  }
}

// Shopping list checked state
export function getShoppingChecked(): Record<string, boolean> {
  return safeGet<Record<string, boolean>>(KEYS.SHOPPING_CHECKED, {});
}

export function saveShoppingChecked(checked: Record<string, boolean>) {
  safeSet(KEYS.SHOPPING_CHECKED, checked);
}
