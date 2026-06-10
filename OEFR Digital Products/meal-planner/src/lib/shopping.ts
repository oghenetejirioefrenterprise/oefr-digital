import { WeekPlan, ShoppingList, ShoppingItem, IngredientCategory, Recipe } from "./types";
import { BUILT_IN_RECIPES } from "./recipes";

export function generateShoppingList(plan: WeekPlan, customRecipes: Recipe[]): ShoppingList {
  const allRecipes = [...BUILT_IN_RECIPES, ...customRecipes];
  const ingredientMap = new Map<string, ShoppingItem>();

  for (const day of Object.values(plan)) {
    for (const meals of Object.values(day)) {
      for (const meal of meals) {
        const recipe = allRecipes.find((r) => r.id === meal.recipeId);
        if (!recipe) continue;
        const multiplier = meal.servings / recipe.servings;

        for (const ing of recipe.ingredients) {
          const key = `${ing.name.toLowerCase()}__${ing.unit}__${ing.category}`;
          const existing = ingredientMap.get(key);
          if (existing) {
            existing.totalAmount += ing.amount * multiplier;
            if (!existing.recipes.includes(recipe.name)) {
              existing.recipes.push(recipe.name);
            }
          } else {
            ingredientMap.set(key, {
              ingredient: { ...ing },
              totalAmount: ing.amount * multiplier,
              checked: false,
              recipes: [recipe.name],
            });
          }
        }
      }
    }
  }

  const shoppingList: ShoppingList = {};
  for (const item of ingredientMap.values()) {
    const cat = item.ingredient.category as IngredientCategory;
    if (!shoppingList[cat]) shoppingList[cat] = [];
    shoppingList[cat]!.push({
      ...item,
      totalAmount: Math.ceil(item.totalAmount * 10) / 10,
    });
  }

  // Sort each category alphabetically
  for (const cat of Object.keys(shoppingList) as IngredientCategory[]) {
    shoppingList[cat]!.sort((a, b) =>
      a.ingredient.name.localeCompare(b.ingredient.name)
    );
  }

  return shoppingList;
}

export function getDayNutrition(
  dayPlan: WeekPlan[string],
  allRecipes: Recipe[]
) {
  let calories = 0, protein = 0, carbs = 0, fat = 0;
  for (const meals of Object.values(dayPlan)) {
    for (const meal of meals) {
      const recipe = allRecipes.find((r) => r.id === meal.recipeId);
      if (!recipe) continue;
      const multiplier = meal.servings / recipe.servings;
      calories += recipe.nutrition.calories * multiplier;
      protein += recipe.nutrition.protein * multiplier;
      carbs += recipe.nutrition.carbs * multiplier;
      fat += recipe.nutrition.fat * multiplier;
    }
  }
  return {
    calories: Math.round(calories),
    protein: Math.round(protein),
    carbs: Math.round(carbs),
    fat: Math.round(fat),
  };
}
