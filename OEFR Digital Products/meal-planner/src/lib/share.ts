import { WeekPlan, DAYS, MEAL_SLOTS, MealSlot, Recipe, ShoppingList, IngredientCategory } from "./types";

const WATERMARK = "Planned with MealCraft Pro — meal-planner-taupe-one.vercel.app";

// Colors matching the app dark theme
const C = {
  bg: "#060d1a",
  card: "#0d1526",
  border: "#1e3a5f",
  lime: "#84cc16",
  limeDark: "#65a30d",
  white: "#ffffff",
  slate100: "#e2e8f0",
  slate300: "#cbd5e1",
  slate400: "#94a3b8",
  slate500: "#64748b",
  slate600: "#475569",
  navy700: "#1e3a5f",
  navy800: "#0f1d32",
  // Slot accent colors
  amber: "#fbbf24",
  green: "#4ade80",
  blue: "#60a5fa",
  purple: "#c084fc",
};

const SLOT_COLORS: Record<MealSlot, string> = {
  Breakfast: C.amber,
  Lunch: C.green,
  Dinner: C.blue,
  Snacks: C.purple,
};

const CATEGORY_EMOJIS: Record<IngredientCategory, string> = {
  Produce: "🥦", Dairy: "🥛", Protein: "🥩", Grains: "🌾",
  Pantry: "🫙", Frozen: "🧊", Beverages: "🥤", Other: "📦",
};

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function truncateText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let t = text;
  while (t.length > 0 && ctx.measureText(t + "…").width > maxWidth) {
    t = t.slice(0, -1);
  }
  return t + "…";
}

// ——— Generate Meal Plan Share Card ———
export function generateMealPlanCard(plan: WeekPlan, allRecipes: Recipe[]): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  const dpr = 2;
  const W = 1080;
  const H = 1350;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + "px";
  canvas.style.height = H + "px";
  const ctx = canvas.getContext("2d")!;
  ctx.scale(dpr, dpr);

  // Background
  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);

  // Subtle gradient overlay
  const grad = ctx.createLinearGradient(0, 0, W, H);
  grad.addColorStop(0, "rgba(132, 204, 22, 0.03)");
  grad.addColorStop(1, "rgba(30, 58, 95, 0.05)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  const pad = 40;
  let y = pad;

  // Title block
  ctx.fillStyle = C.lime;
  ctx.font = "bold 36px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  ctx.fillText("🍽️ My Weekly Meal Plan", pad, y + 36);
  y += 52;
  ctx.fillStyle = C.slate500;
  ctx.font = "14px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  ctx.fillText("MealCraft Pro", pad, y + 14);
  y += 36;

  // Divider
  ctx.fillStyle = C.navy700;
  ctx.fillRect(pad, y, W - pad * 2, 1);
  y += 20;

  // Compute stats
  let totalMeals = 0;
  const recipeIds = new Set<string>();
  const tagSet = new Set<string>();
  for (const day of DAYS) {
    for (const slot of MEAL_SLOTS) {
      for (const meal of plan[day]?.[slot] ?? []) {
        totalMeals++;
        recipeIds.add(meal.recipeId);
        const recipe = allRecipes.find((r) => r.id === meal.recipeId);
        if (recipe) recipe.tags.forEach((t) => tagSet.add(t));
      }
    }
  }

  // Stats row
  const stats = [
    { label: "Meals Planned", value: String(totalMeals), color: C.lime },
    { label: "Unique Recipes", value: String(recipeIds.size), color: C.blue },
    { label: "Dietary Tags", value: String(tagSet.size), color: C.purple },
  ];
  const statW = (W - pad * 2 - 20) / 3;
  stats.forEach((s, i) => {
    const sx = pad + i * (statW + 10);
    ctx.fillStyle = C.navy800;
    roundRect(ctx, sx, y, statW, 70, 12);
    ctx.fill();
    ctx.strokeStyle = C.border;
    ctx.lineWidth = 1;
    roundRect(ctx, sx, y, statW, 70, 12);
    ctx.stroke();
    ctx.fillStyle = s.color;
    ctx.font = "bold 28px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    ctx.fillText(s.value, sx + 16, y + 34);
    ctx.fillStyle = C.slate500;
    ctx.font = "12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    ctx.fillText(s.label, sx + 16, y + 54);
  });
  y += 90;

  // Dietary tags
  if (tagSet.size > 0) {
    ctx.font = "bold 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    let tx = pad;
    for (const tag of tagSet) {
      const tw = ctx.measureText(tag).width + 20;
      ctx.fillStyle = "rgba(132, 204, 22, 0.1)";
      roundRect(ctx, tx, y, tw, 26, 6);
      ctx.fill();
      ctx.strokeStyle = "rgba(132, 204, 22, 0.3)";
      ctx.lineWidth = 1;
      roundRect(ctx, tx, y, tw, 26, 6);
      ctx.stroke();
      ctx.fillStyle = C.lime;
      ctx.fillText(tag, tx + 10, y + 17);
      tx += tw + 8;
    }
    y += 42;
  }

  // Weekly grid
  const colW = (W - pad * 2 - 80) / 7;
  const headerH = 32;

  // Day headers
  ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  DAYS.forEach((day, i) => {
    const dx = pad + 80 + i * colW;
    ctx.fillStyle = C.navy800;
    roundRect(ctx, dx + 2, y, colW - 4, headerH, 8);
    ctx.fill();
    ctx.fillStyle = C.lime;
    ctx.textAlign = "center";
    ctx.fillText(day.slice(0, 3), dx + colW / 2, y + 21);
  });
  ctx.textAlign = "left";
  y += headerH + 8;

  // Meal rows
  const rowH = Math.min(180, (H - y - 100) / 4);

  MEAL_SLOTS.forEach((slot) => {
    // Slot label
    ctx.fillStyle = SLOT_COLORS[slot];
    ctx.font = "bold 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(slot.toUpperCase(), pad + 72, y + 20);
    ctx.textAlign = "left";

    DAYS.forEach((day, i) => {
      const dx = pad + 80 + i * colW;
      const meals = plan[day]?.[slot] ?? [];

      // Cell background
      ctx.fillStyle = C.card;
      roundRect(ctx, dx + 2, y, colW - 4, rowH - 4, 10);
      ctx.fill();
      ctx.strokeStyle = C.border;
      ctx.lineWidth = 0.5;
      roundRect(ctx, dx + 2, y, colW - 4, rowH - 4, 10);
      ctx.stroke();

      if (meals.length === 0) {
        ctx.fillStyle = C.slate600;
        ctx.font = "11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("—", dx + colW / 2, y + rowH / 2 + 4);
        ctx.textAlign = "left";
      } else {
        let my = y + 10;
        for (const meal of meals.slice(0, 3)) {
          const recipe = allRecipes.find((r) => r.id === meal.recipeId);
          if (!recipe) continue;
          ctx.fillStyle = C.slate100;
          ctx.font = "bold 10px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
          const name = truncateText(ctx, recipe.name, colW - 16);
          ctx.fillText(name, dx + 8, my + 10);
          // Calorie badge
          const cal = Math.round((recipe.nutrition.calories * meal.servings) / recipe.servings);
          ctx.fillStyle = C.slate500;
          ctx.font = "9px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
          ctx.fillText(`${cal} cal`, dx + 8, my + 22);
          my += 30;
        }
        if (meals.length > 3) {
          ctx.fillStyle = C.slate500;
          ctx.font = "9px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
          ctx.fillText(`+${meals.length - 3} more`, dx + 8, my + 10);
        }
      }
    });

    y += rowH;
  });

  // Watermark
  y = H - pad;
  ctx.fillStyle = C.slate600;
  ctx.font = "12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(WATERMARK, W / 2, y);
  ctx.textAlign = "left";

  // Subtle border around entire card
  ctx.strokeStyle = C.border;
  ctx.lineWidth = 1;
  roundRect(ctx, 1, 1, W - 2, H - 2, 20);
  ctx.stroke();

  return canvas;
}

// ——— Generate Shopping List Share Card ———
export function generateShoppingListCard(
  list: ShoppingList,
  quantities: Record<string, number>
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  const dpr = 2;
  const W = 720;
  const pad = 36;

  // Pre-calculate height
  const categoryOrder: IngredientCategory[] = ["Produce", "Protein", "Dairy", "Grains", "Pantry", "Frozen", "Beverages", "Other"];
  const activeCats = categoryOrder.filter((cat) => (list[cat]?.length ?? 0) > 0);
  let totalHeight = 160; // header + stats
  for (const cat of activeCats) {
    totalHeight += 44; // category header
    totalHeight += (list[cat]?.length ?? 0) * 32; // items
    totalHeight += 16; // spacing
  }
  totalHeight += 60; // watermark

  const H = Math.max(600, totalHeight);
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + "px";
  canvas.style.height = H + "px";
  const ctx = canvas.getContext("2d")!;
  ctx.scale(dpr, dpr);

  // Background
  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "rgba(132, 204, 22, 0.02)");
  grad.addColorStop(1, "rgba(30, 58, 95, 0.04)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  let y = pad;

  // Title
  ctx.fillStyle = C.lime;
  ctx.font = "bold 30px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  ctx.fillText("🛒 Shopping List", pad, y + 30);
  y += 46;

  // Item count
  const totalItems = Object.values(list).reduce((s, items) => s + (items?.length ?? 0), 0);
  ctx.fillStyle = C.slate500;
  ctx.font = "14px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  ctx.fillText(`${totalItems} items · ${activeCats.length} categories`, pad, y + 14);
  y += 32;

  // Divider
  ctx.fillStyle = C.navy700;
  ctx.fillRect(pad, y, W - pad * 2, 1);
  y += 20;

  // Categories
  const catColors: Record<IngredientCategory, string> = {
    Produce: C.green, Dairy: C.blue, Protein: "#f87171", Grains: C.amber,
    Pantry: C.slate400, Frozen: "#22d3ee", Beverages: C.purple, Other: C.slate500,
  };

  for (const cat of activeCats) {
    const items = list[cat] ?? [];
    const emoji = CATEGORY_EMOJIS[cat];
    const color = catColors[cat];

    // Category header
    ctx.fillStyle = color;
    ctx.font = "bold 15px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    ctx.fillText(`${emoji} ${cat}`, pad, y + 15);

    // Item count badge
    const countText = `${items.length}`;
    const countW = ctx.measureText(countText).width + 16;
    ctx.fillStyle = "rgba(255,255,255,0.06)";
    roundRect(ctx, pad + ctx.measureText(`${emoji} ${cat}  `).width + 4, y + 1, countW, 20, 10);
    ctx.fill();
    ctx.fillStyle = C.slate500;
    ctx.font = "11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    ctx.fillText(countText, pad + ctx.measureText(`${emoji} ${cat}  `).width + 12, y + 15);

    y += 30;

    // Items
    for (const item of items) {
      const key = `${item.ingredient.name}__${item.ingredient.unit}`;
      const qty = quantities[key] ?? item.totalAmount;

      // Checkbox circle
      ctx.strokeStyle = C.navy700;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(pad + 10, y + 10, 7, 0, Math.PI * 2);
      ctx.stroke();

      // Item name
      ctx.fillStyle = C.slate100;
      ctx.font = "13px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
      ctx.fillText(item.ingredient.name, pad + 28, y + 14);

      // Quantity on right
      const qtyText = `${qty} ${item.ingredient.unit}`;
      ctx.fillStyle = C.slate400;
      ctx.font = "12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(qtyText, W - pad, y + 14);
      ctx.textAlign = "left";

      y += 30;
    }

    y += 12;
  }

  // Watermark
  y = H - pad;
  ctx.fillStyle = C.slate600;
  ctx.font = "11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(WATERMARK, W / 2, y);
  ctx.textAlign = "left";

  // Border
  ctx.strokeStyle = C.border;
  ctx.lineWidth = 1;
  roundRect(ctx, 1, 1, W - 2, H - 2, 16);
  ctx.stroke();

  return canvas;
}

// ——— Download & Share helpers ———
export function downloadCanvasAsPng(canvas: HTMLCanvasElement, filename: string) {
  const link = document.createElement("a");
  link.download = filename;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

export async function shareCanvas(canvas: HTMLCanvasElement, title: string, text: string) {
  try {
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/png")
    );
    if (!blob) throw new Error("Failed to create blob");

    if (navigator.canShare?.({ files: [new File([blob], "share.png", { type: "image/png" })] })) {
      await navigator.share({
        title,
        text,
        files: [new File([blob], "mealcraft-share.png", { type: "image/png" })],
      });
      return true;
    }
  } catch (e) {
    if ((e as Error).name === "AbortError") return false;
  }
  // Fallback: download
  downloadCanvasAsPng(canvas, "mealcraft-share.png");
  return false;
}
