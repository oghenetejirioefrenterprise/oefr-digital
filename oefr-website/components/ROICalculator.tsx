"use client";

import { useState } from "react";

export default function ROICalculator() {
  const [coldContacts, setColdContacts] = useState<string>("500");
  const [avgClientValue, setAvgClientValue] = useState<string>("1200");
  const [assumedRate, setAssumedRate] = useState<string>("1");

  const contacts = parseInt(coldContacts) || 0;
  const value = parseFloat(avgClientValue) || 0;
  const rate = Math.max(0, Math.min(parseFloat(assumedRate) || 0, 100));
  const recoveredClients = Math.round(contacts * (rate / 100));
  const recoveredRevenue = recoveredClients * value;

  return (
    <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-8 sm:p-10 backdrop-blur">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center rounded-full border border-emerald-500/25 bg-emerald-500/10 px-4 py-1.5 text-sm font-medium text-emerald-400 mb-4">
          📊 Scenario Planner
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white">
          What Could a Reactivation Test Be Worth?
        </h2>
        <p className="mt-2 text-slate-400">Model your own assumptions before deciding whether a pilot is worth testing</p>
      </div>

      {/* Inputs */}
      <div className="grid sm:grid-cols-3 gap-6 mb-8">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Number of cold contacts
          </label>
          <input
            type="number"
            min="0"
            value={coldContacts}
            onChange={(e) => setColdContacts(e.target.value)}
            placeholder="e.g. 500"
            className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
          />
          <p className="mt-1 text-xs text-slate-500">Contacts with 90+ days no engagement</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Average client value ($)
          </label>
          <input
            type="number"
            min="0"
            value={avgClientValue}
            onChange={(e) => setAvgClientValue(e.target.value)}
            placeholder="e.g. 1200"
            className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
          />
          <p className="mt-1 text-xs text-slate-500">Annual value per reactivated client</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Assumed rebooking rate (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={assumedRate}
            onChange={(e) => setAssumedRate(e.target.value)}
            placeholder="e.g. 1"
            className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
          />
          <p className="mt-1 text-xs text-slate-500">Your assumption, not a promised result</p>
        </div>
      </div>

      {/* Result */}
      <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-6 text-center">
        <p className="text-sm text-blue-300 mb-3">If {rate.toLocaleString()}% of these contacts rebook:</p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8">
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-white">
              {recoveredClients.toLocaleString()}
            </div>
            <div className="text-sm text-slate-400 mt-1">clients reactivated</div>
          </div>
          <div className="text-2xl text-slate-600 hidden sm:block">=</div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              ${recoveredRevenue.toLocaleString()}
            </div>
            <div className="text-sm text-slate-400 mt-1">recovered revenue</div>
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-500">
          Planning estimate only. Actual results depend on list quality, permission, offer, sender reputation, and follow-up.
        </p>
      </div>
    </div>
  );
}
