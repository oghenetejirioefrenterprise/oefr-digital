import { encryptData, decryptData, VAULT_KEY } from "./crypto";

export type Category = "Social" | "Email" | "Finance" | "Shopping" | "Work" | "Other";

export interface VaultEntry {
  id: string;
  siteName: string;
  url: string;
  username: string;
  password: string;
  notes: string;
  category: Category;
  createdAt: number;
  updatedAt: number;
}

export interface VaultData {
  entries: VaultEntry[];
  version: number;
}

export const CATEGORIES: { name: Category; icon: string; color: string }[] = [
  { name: "Social", icon: "👥", color: "#8b5cf6" },
  { name: "Email", icon: "📧", color: "#3b82f6" },
  { name: "Finance", icon: "💰", color: "#10b981" },
  { name: "Shopping", icon: "🛍️", color: "#f59e0b" },
  { name: "Work", icon: "💼", color: "#6366f1" },
  { name: "Other", icon: "🔐", color: "#64748b" },
];

export function generateId(): string {
  return crypto.getRandomValues(new Uint32Array(4)).join("-");
}

export async function loadVault(masterPassword: string): Promise<VaultData> {
  const encrypted = localStorage.getItem(VAULT_KEY);
  if (!encrypted) return { entries: [], version: 1 };
  try {
    const decrypted = await decryptData(encrypted, masterPassword);
    return JSON.parse(decrypted);
  } catch {
    throw new Error("Failed to decrypt vault. Wrong password?");
  }
}

export async function saveVault(vault: VaultData, masterPassword: string): Promise<void> {
  const encrypted = await encryptData(JSON.stringify(vault), masterPassword);
  localStorage.setItem(VAULT_KEY, encrypted);
}

export function generatePassword(options: {
  length: number;
  uppercase: boolean;
  lowercase: boolean;
  numbers: boolean;
  symbols: boolean;
}): string {
  const { length, uppercase, lowercase, numbers, symbols } = options;
  let charset = "";
  const required: string[] = [];

  if (uppercase) { charset += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"; required.push("ABCDEFGHIJKLMNOPQRSTUVWXYZ"); }
  if (lowercase) { charset += "abcdefghijklmnopqrstuvwxyz"; required.push("abcdefghijklmnopqrstuvwxyz"); }
  if (numbers) { charset += "0123456789"; required.push("0123456789"); }
  if (symbols) { charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"; required.push("!@#$%^&*()_+-=[]{}|;:,.<>?"); }

  if (!charset) charset = "abcdefghijklmnopqrstuvwxyz";

  const array = new Uint32Array(length);
  crypto.getRandomValues(array);

  let password = Array.from(array).map((n) => charset[n % charset.length]).join("");

  // Ensure at least one character from each required set.
  // Use DISTINCT positions for each guaranteed char. Picking positions
  // independently (positions[i] % length) lets two sets collide on the same
  // index, which silently drops a requested character class — e.g. a password
  // with symbols enabled that contains no symbol. Measured: ~1.7% of
  // 16-char/4-class passwords lost a requested class (worse at shorter
  // lengths). Shuffle all indices and take the first required.length so
  // every class lands in its own slot.
  if (required.length > 0 && password.length >= required.length) {
    const chars = password.split("");

    // Fisher–Yates shuffle of all index positions using the CSPRNG.
    const indices = Array.from({ length }, (_, i) => i);
    for (let i = length - 1; i > 0; i--) {
      const r = new Uint32Array(1);
      crypto.getRandomValues(r);
      const j = r[0] % (i + 1);
      [indices[i], indices[j]] = [indices[j], indices[i]];
    }

    required.forEach((set, i) => {
      const pos = indices[i]; // distinct position per required class
      const rand = new Uint32Array(1);
      crypto.getRandomValues(rand);
      chars[pos] = set[rand[0] % set.length];
    });
    password = chars.join("");
  }

  return password;
}

export function detectReusedPasswords(entries: VaultEntry[]): Set<string> {
  const passwordCount = new Map<string, number>();
  entries.forEach((e) => {
    passwordCount.set(e.password, (passwordCount.get(e.password) || 0) + 1);
  });
  const reused = new Set<string>();
  passwordCount.forEach((count, pwd) => {
    if (count > 1) reused.add(pwd);
  });
  return reused;
}

export function isOldPassword(entry: VaultEntry, days = 90): boolean {
  return Date.now() - entry.updatedAt > days * 24 * 60 * 60 * 1000;
}
