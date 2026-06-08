// Canonical Stripe price IDs for entitlement binding.
//
// All OEFR products share ONE Stripe account, so a "paid" session alone is NOT
// proof the buyer purchased a specific item — entitlement checks must bind to
// the exact price ID. Keep these IDs in one place so the download route and the
// thank-you page can never drift apart.

export const SSDI_PRICE_ID = "price_1TaMgU3H4Cmk8ulCzJDrS7qS"; // SSDI Hearing Evidence Letter Kit ($14)
