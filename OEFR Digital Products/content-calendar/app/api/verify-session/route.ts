import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";

export async function GET(request: NextRequest) {
  const sessionId = request.nextUrl.searchParams.get("session_id");

  if (!sessionId) {
    return NextResponse.json({ verified: false, error: "No session_id provided" }, { status: 400 });
  }

  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) {
    // Stripe key not configured — reject to prevent unintentional free access in production
    return NextResponse.json({ verified: false, error: "Payment verification not configured" }, { status: 500 });
  }

  try {
    const stripe = new Stripe(stripeKey, {
      apiVersion: "2026-02-25.clover",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.retrieve(sessionId);

    // SECURITY: All OEFR products share ONE Stripe account. A bare
    // payment_status === "paid" check lets any paid session_id from any other
    // product (e.g. the $14 SSDI kit) unlock Postify Pro for free. Bind the
    // entitlement to THIS product: correct price ($29 USD) AND this SKU's
    // metadata.product tag (set on both checkout paths).
    const isThisProduct =
      session.payment_status === "paid" &&
      session.currency === "usd" &&
      session.amount_total === 2900 &&
      session.metadata?.product === "postify_pro";

    if (isThisProduct) {
      return NextResponse.json({ verified: true });
    }

    return NextResponse.json({ verified: false, error: "Payment not completed" });
  } catch (error) {
    console.error("Session verification error:", error);
    return NextResponse.json({ verified: false, error: "Invalid session" }, { status: 400 });
  }
}
