import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";

export async function GET(request: NextRequest) {
  // Redirect to POST handler via form for simplicity, or handle GET for direct link
  const url = new URL(request.url);
  const baseUrl = `${url.protocol}//${url.host}`;

  if (!process.env.STRIPE_SECRET_KEY) {
    // Fallback: if no Stripe key, show a page to manually grant access (dev mode)
    return NextResponse.redirect(`${baseUrl}/app/gate`);
  }

  try {
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2026-02-25.clover",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "payment",
      allow_promotion_codes: true,
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: {
              name: "MealCraft Pro — Lifetime Access",
              description:
                "Full 7-day meal planner, 50+ recipes, shopping list, nutrition tracking. One-time payment, yours forever.",
              images: [],
            },
            unit_amount: 2700, // $27.00
          },
          quantity: 1,
        },
      ],
      success_url: `${baseUrl}/api/checkout/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/#pricing`,
      metadata: {
        product: "mealcraft_pro_lifetime",
      },
    });

    return NextResponse.redirect(session.url!, 303);
  } catch (error) {
    console.error("Stripe checkout error:", error);
    return NextResponse.json(
      { error: "Failed to create checkout session" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  return GET(request);
}
