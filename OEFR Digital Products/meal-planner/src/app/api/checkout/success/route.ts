import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const baseUrl = `${url.protocol}//${url.host}`;
  const sessionId = url.searchParams.get("session_id");

  if (!process.env.STRIPE_SECRET_KEY || !sessionId) {
    return NextResponse.redirect(`${baseUrl}/app/gate`);
  }

  try {
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2026-02-25.clover",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.retrieve(sessionId);

    // SECURITY: all OEFR products share ONE Stripe account, so a bare
    // payment_status check lets ANY paid session_id from any product
    // (e.g. a cheaper $14 kit) unlock MealCraft Pro. Bind entitlement to
    // THIS product + exact amount + currency (same class as the
    // verify-session paywall-bypass fixes across the catalog).
    if (
      session.payment_status === "paid" &&
      session.metadata?.product === "mealcraft_pro_lifetime" &&
      session.amount_total === 2700 &&
      session.currency === "usd"
    ) {
      // Redirect to a success page that grants access via localStorage
      return NextResponse.redirect(`${baseUrl}/app/success?verified=1`);
    }
  } catch (error) {
    console.error("Stripe verify error:", error);
  }

  return NextResponse.redirect(`${baseUrl}/app/gate`);
}
