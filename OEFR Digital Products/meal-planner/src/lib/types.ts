export type DietaryTag = "Vegetarian" | "Vegan" | "Keto" | "Gluten-Free" | "High-Protein";

export type IngredientCategory =
  | "Produce"
  | "Dairy"
  | "Protein"
  | "Grains"
  | "Pantry"
  | "Frozen"
  | "Beverages"
  | "Other";

export interface Ingredient {
  name: string;
  amount: number;
  unit: string;
  category: IngredientCategory;
}

export interface Nutrition {
  calories: number;
  protein: number; // grams
  carbs: number;   // grams
  fat: number;     // grams
}

export interface Recipe {
  id: string;
  name: string;
  description: string;
  servings: number;
  prepTime: number;  // minutes
  cookTime: number;  // minutes
  imageUrl?: string;
  tags: DietaryTag[];
  ingredients: Ingredient[];
  steps: string[];
  nutrition: Nutrition; // per serving
  isCustom?: boolean;
}

export type MealSlot = "Breakfast" | "Lunch" | "Dinner" | "Snacks";

export const DAYS: string[] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const MEAL_SLOTS: MealSlot[] = ["Breakfast", "Lunch", "Dinner", "Snacks"];

export interface PlannedMeal {
  id: string;
  recipeId: string;
  servings: number;
}

export type DayPlan = {
  [slot in MealSlot]: PlannedMeal[];
};

export type WeekPlan = {
  [day: string]: DayPlan;
};

export interface SavedPlan {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  plan: WeekPlan;
}

export interface ShoppingItem {
  ingredient: Ingredient;
  totalAmount: number;
  checked: boolean;
  recipes: string[]; // recipe names using this ingredient
}

export type ShoppingList = {
  [category in IngredientCategory]?: ShoppingItem[];
};

export interface UserSettings {
  dietaryRestrictions: DietaryTag[];
  defaultServings: number;
  showNutrition: boolean;
  theme: "dark";
}

export const DEFAULT_SETTINGS: UserSettings = {
  dietaryRestrictions: [],
  defaultServings: 2,
  showNutrition: true,
  theme: "dark",
};
