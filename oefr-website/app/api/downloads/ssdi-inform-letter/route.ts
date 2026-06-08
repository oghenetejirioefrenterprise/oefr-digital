import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";
import { SSDI_PRICE_ID } from "@/lib/stripe-prices";

/**
 * Protected download endpoint for the SSDI 5-Day INFORM Letter Kit PDF.
 * Verifies the Stripe checkout session before serving the file.
 * The PDF lives outside public/ so it cannot be hotlinked / paywall-bypassed.
 */

const PDF_PATH = join(
  process.cwd(),
  "data",
  "protected-downloads",
  "SSDI-5-Day-INFORM-Letter-Kit.pdf",
);

// All OEFR products share ONE Stripe account, so a "paid" session alone is NOT
// proof the buyer purchased THIS item. An amount floor is insufficient too:
// >= $14 lets any pricier SKU escalate, and two OTHER products also cost $14.
// Bind to the exact SSDI Stripe price (SSDI_PRICE_ID, shared with the thank-you
// page) so only a session that actually bought this product unlocks the file.
// Fails closed.

export async function GET(req: NextRequest) {
  const sessionId = req.nextUrl.searchParams.get("session_id");

  if (!sessionId) {
    return NextResponse.json({ error: "Missing session_id" }, { status: 401 });
  }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) {
    console.error("[api/downloads/ssdi-inform-letter] STRIPE_SECRET_KEY missing");
    return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
  }

  try {
    const Stripe = (await import("stripe")).default;
    const stripe = new Stripe(stripeKey, {
      apiVersion: "2024-12-18.acacia" as any,
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.retrieve(sessionId, {
      expand: ["line_items"],
    });
    const isPaid = session.payment_status === "paid";
    const purchasedThisProduct = (session.line_items?.data ?? []).some(
      (li) => li.price?.id === SSDI_PRICE_ID,
    );

    if (!isPaid || !purchasedThisProduct) {
      console.warn(
        `[api/downloads/ssdi-inform-letter] session ${sessionId} refused ` +
          `(payment_status=${session.payment_status}, purchasedThisProduct=${purchasedThisProduct})`,
      );
      return NextResponse.json(
        { error: "Payment not verified for this product" },
        { status: 403 },
      );
    }

    // Serve the file
    const fileBuffer = await readFile(PDF_PATH);

    return new NextResponse(fileBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": 'attachment; filename="SSDI-5-Day-INFORM-Letter-Kit.pdf"',
        "Content-Length": String(fileBuffer.length),
        "Cache-Control": "private, no-store",
      },
    });
  } catch (err) {
    console.error("[api/downloads/ssdi-inform-letter] Error:", err);
    return NextResponse.json({ error: "Download failed" }, { status: 500 });
  }
}
