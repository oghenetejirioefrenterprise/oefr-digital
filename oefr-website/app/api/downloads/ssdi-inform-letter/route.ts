import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

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

// This product is $14. The shared Stripe account sells many products, so a
// "paid" session alone is NOT proof the buyer purchased THIS item — without an
// amount floor, any cheaper paid session_id would unlock this file. Gate on the
// minimum expected amount + currency so a lower-priced session cannot escalate
// to this download.
const MIN_AMOUNT_TOTAL = 1400; // $14.00 in cents
const EXPECTED_CURRENCY = "usd";

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

    const session = await stripe.checkout.sessions.retrieve(sessionId);
    const isPaid = session.payment_status === "paid" || session.status === "complete";

    if (!isPaid) {
      return NextResponse.json({ error: "Payment not verified" }, { status: 403 });
    }

    // Confirm the session actually purchased THIS product, not just *a* product
    // on the shared Stripe account (cross-product paywall-bypass guard).
    const amountOk =
      typeof session.amount_total === "number" && session.amount_total >= MIN_AMOUNT_TOTAL;
    const currencyOk = (session.currency ?? "").toLowerCase() === EXPECTED_CURRENCY;
    if (!amountOk || !currencyOk) {
      console.warn(
        `[api/downloads/ssdi-inform-letter] session ${sessionId} paid but amount/currency mismatch ` +
          `(amount_total=${session.amount_total}, currency=${session.currency}) — refusing download`,
      );
      return NextResponse.json({ error: "Purchase does not match this product" }, { status: 403 });
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
