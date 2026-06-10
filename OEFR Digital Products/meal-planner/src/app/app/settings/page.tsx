"use client";
import { useState, useEffect } from "react";
import { getSettings, saveSettings } from "@/lib/storage";
import { UserSettings, DietaryTag } from "@/lib/types";
import { Settings, Save, CheckCircle, Leaf } from "lucide-react";

const DIET_TAGS: DietaryTag[] = ["Vegetarian", "Vegan", "Keto", "Gluten-Free", "High-Protein"];

const TAG_DESCRIPTIONS: Record<DietaryTag, string> = {
  Vegetarian: "No meat or fish, but dairy and eggs are allowed",
  Vegan: "No animal products whatsoever",
  Keto: "Very low carb, high fat — typically <50g carbs/day",
  "Gluten-Free": "No wheat, barley, rye, or other gluten-containing grains",
  "High-Protein": "Focus on recipes with 20g+ protein per serving",
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>({
    dietaryRestrictions: [],
    defaultServings: 2,
    showNutrition: true,
    theme: "dark",
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(getSettings());
  }, []);

  const toggleTag = (tag: DietaryTag) => {
    setSettings((s) => ({
      ...s,
      dietaryRestrictions: s.dietaryRestrictions.includes(tag)
        ? s.dietaryRestrictions.filter((t) => t !== tag)
        : [...s.dietaryRestrictions, tag],
    }));
  };

  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-slate-500 text-sm">Customize your meal planning experience</p>
        </div>
        <button
          onClick={handleSave}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm transition-all ${
            saved
              ? "bg-green-500/20 text-green-400 border border-green-500/30"
              : "bg-lime-500 text-navy-950 hover:bg-lime-400"
          }`}
        >
          {saved ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </div>

      <div className="space-y-6">
        {/* Dietary restrictions */}
        <div className="bg-navy-900 rounded-2xl border border-navy-700 p-6">
          <div className="flex items-center gap-2 mb-1">
            <Leaf className="w-5 h-5 text-lime-400" />
            <h2 className="text-white font-semibold">Dietary Restrictions</h2>
          </div>
          <p className="text-slate-500 text-sm mb-4">
            Selected tags will be highlighted in the recipe browser and used for filtering.
          </p>
          <div className="space-y-3">
            {DIET_TAGS.map((tag) => {
              const active = settings.dietaryRestrictions.includes(tag);
              return (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-colors text-left ${
                    active
                      ? "bg-lime-500/10 border-lime-500/30"
                      : "bg-navy-800 border-navy-700 hover:border-navy-600"
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                      active ? "bg-lime-500 border-lime-500" : "border-navy-500"
                    }`}
                  >
                    {active && (
                      <svg className="w-3 h-3 text-navy-950" fill="none" viewBox="0 0 12 12">
                        <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  <div>
                    <div className={`text-sm font-medium ${active ? "text-lime-400" : "text-white"}`}>{tag}</div>
                    <div className="text-xs text-slate-500">{TAG_DESCRIPTIONS[tag]}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Preferences */}
        <div className="bg-navy-900 rounded-2xl border border-navy-700 p-6">
          <div className="flex items-center gap-2 mb-1">
            <Settings className="w-5 h-5 text-slate-400" />
            <h2 className="text-white font-semibold">Preferences</h2>
          </div>
          <p className="text-slate-500 text-sm mb-4">General planner preferences.</p>

          <div className="space-y-4">
            {/* Default servings */}
            <div className="flex items-center justify-between">
              <div>
                <div className="text-white text-sm font-medium">Default Servings</div>
                <div className="text-slate-500 text-xs">How many servings to default to when adding a recipe</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSettings((s) => ({ ...s, defaultServings: Math.max(1, s.defaultServings - 1) }))}
                  className="w-8 h-8 rounded-lg bg-navy-800 text-white hover:bg-navy-700 flex items-center justify-center font-bold"
                >−</button>
                <span className="text-white font-bold w-6 text-center">{settings.defaultServings}</span>
                <button
                  onClick={() => setSettings((s) => ({ ...s, defaultServings: Math.min(12, s.defaultServings + 1) }))}
                  className="w-8 h-8 rounded-lg bg-navy-800 text-white hover:bg-navy-700 flex items-center justify-center font-bold"
                >+</button>
              </div>
            </div>

            {/* Show nutrition */}
            <div className="flex items-center justify-between">
              <div>
                <div className="text-white text-sm font-medium">Show Nutrition Overview</div>
                <div className="text-slate-500 text-xs">Display daily calorie and macro bars on the planner</div>
              </div>
              <button
                onClick={() => setSettings((s) => ({ ...s, showNutrition: !s.showNutrition }))}
                className={`relative w-11 h-6 rounded-full transition-colors ${settings.showNutrition ? "bg-lime-500" : "bg-navy-700"}`}
              >
                <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${settings.showNutrition ? "translate-x-6" : "translate-x-1"}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Data info */}
        <div className="bg-navy-900 rounded-2xl border border-navy-700 p-6">
          <h2 className="text-white font-semibold mb-1">Your Data</h2>
          <p className="text-slate-500 text-sm mb-4">
            All your meal plans, custom recipes, and settings are stored locally in your browser via <code className="text-lime-400 text-xs">localStorage</code>. 
            Nothing ever leaves your device.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => {
                if (confirm("This will clear all your meal plans, recipes, and settings. Are you sure?")) {
                  localStorage.clear();
                  window.location.reload();
                }
              }}
              className="px-4 py-2 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20 text-sm hover:bg-red-500/20 transition-colors font-medium"
            >
              Clear All Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
