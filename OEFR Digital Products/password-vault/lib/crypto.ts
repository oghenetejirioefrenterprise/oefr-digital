// AES-256-GCM encryption using Web Crypto API
// Key derivation: PBKDF2 with SHA-256, 310,000 iterations (NIST recommended)

export const SALT_KEY = "pv_salt";
export const VAULT_KEY = "pv_vault";
export const ACCESS_KEY = "pv_access";
export const SETTINGS_KEY = "pv_settings";

export async function deriveKey(password: string, salt: Uint8Array<ArrayBuffer>): Promise<CryptoKey> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt,
      iterations: 310000,
      hash: "SHA-256",
    },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

export async function encryptData(data: string, password: string): Promise<string> {
  let salt: Uint8Array<ArrayBuffer>;
  const storedSalt = localStorage.getItem(SALT_KEY);
  if (storedSalt) {
    salt = new Uint8Array(JSON.parse(storedSalt)) as Uint8Array<ArrayBuffer>;
  } else {
    salt = crypto.getRandomValues(new Uint8Array(32)) as Uint8Array<ArrayBuffer>;
    localStorage.setItem(SALT_KEY, JSON.stringify(Array.from(salt)));
  }

  const key = await deriveKey(password, salt);
  const iv = crypto.getRandomValues(new Uint8Array(12)) as Uint8Array<ArrayBuffer>;
  const encoder = new TextEncoder();
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(data)
  );

  const combined = new Uint8Array(iv.length + encrypted.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encrypted), iv.length);
  return bytesToBase64(combined);
}

// Chunked byte→base64 conversion. `btoa(String.fromCharCode(...bytes))`
// spreads every byte as a function argument, which throws
// "RangeError: Maximum call stack size exceeded" once the ciphertext
// exceeds the engine arg limit (~125KB in V8 — i.e. a vault with a few
// hundred entries + notes). That made saveVault() fail exactly for the
// heaviest users. Reproduced: 150KB ciphertext throws, 32KB OK.
function bytesToBase64(bytes: Uint8Array): string {
  const CHUNK = 0x8000; // 32K args per call — safely under the limit
  let binary = "";
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(binary);
}

export async function decryptData(encryptedB64: string, password: string): Promise<string> {
  const storedSalt = localStorage.getItem(SALT_KEY);
  if (!storedSalt) throw new Error("No salt found");

  const salt = new Uint8Array(JSON.parse(storedSalt)) as Uint8Array<ArrayBuffer>;
  const key = await deriveKey(password, salt);
  const combined = new Uint8Array(
    atob(encryptedB64).split("").map((c) => c.charCodeAt(0))
  );
  const iv = combined.slice(0, 12);
  const data = combined.slice(12);

  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    key,
    data
  );
  return new TextDecoder().decode(decrypted);
}

export async function verifyMasterPassword(password: string): Promise<boolean> {
  try {
    const encrypted = localStorage.getItem(ACCESS_KEY);
    if (!encrypted) return false;
    const decrypted = await decryptData(encrypted, password);
    return decrypted === "VAULT_ACCESS_GRANTED";
  } catch {
    return false;
  }
}

export async function setupMasterPassword(password: string): Promise<void> {
  // Clear old salt so a new one is generated
  localStorage.removeItem(SALT_KEY);
  const encrypted = await encryptData("VAULT_ACCESS_GRANTED", password);
  localStorage.setItem(ACCESS_KEY, encrypted);
}

export function hasVaultSetup(): boolean {
  return !!localStorage.getItem(ACCESS_KEY);
}

// Password strength scorer
export function scorePassword(password: string): {
  score: number;
  label: "weak" | "medium" | "strong" | "very-strong";
  color: string;
  suggestions: string[];
} {
  let score = 0;
  const suggestions: string[] = [];

  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (password.length >= 16) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  else suggestions.push("Add lowercase letters");
  if (/[A-Z]/.test(password)) score += 1;
  else suggestions.push("Add uppercase letters");
  if (/[0-9]/.test(password)) score += 1;
  else suggestions.push("Add numbers");
  if (/[^a-zA-Z0-9]/.test(password)) score += 2;
  else suggestions.push("Add special characters");
  if (password.length < 8) suggestions.push("Use at least 8 characters");

  // Penalize common patterns
  if (/(.)\1{2,}/.test(password)) score -= 1;
  if (/^[0-9]+$/.test(password)) score -= 2;

  score = Math.max(0, Math.min(8, score));

  if (score <= 2) return { score, label: "weak", color: "#ef4444", suggestions };
  if (score <= 4) return { score, label: "medium", color: "#f59e0b", suggestions };
  if (score <= 6) return { score, label: "strong", color: "#10b981", suggestions };
  return { score, label: "very-strong", color: "#06b6d4", suggestions };
}
