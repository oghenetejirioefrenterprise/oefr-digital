import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";

export async function GET(request: NextRequest) {
  // Redirect to Stripe checkout page
  const origin = request.nextUrl.origin;

  if (!process.env.STRIPE_SECRET_KEY) {
    // Dev mode: grant access directly
    return NextResponse.redirect(`${origin}/app?dev=true`);
  }

  try {
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2026-02-25.clover",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: {
              name: "Postify Pro — Content Calendar & Social Media Planner",
              description: "Lifetime access. No subscription. Plan and schedule your social media content across all platforms.",
              images: [],
            },
            unit_amount: 2900, // $29.00
          },
          quantity: 1,
        },
      ],
      mode: "payment",
      success_url: `${origin}/app?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/?checkout=cancelled`,
      metadata: {
        product: "postify_pro",
      },
    });

    return NextResponse.redirect(session.url!);
  } catch (error) {
    console.error("Stripe checkout error:", error);
    return NextResponse.redirect(`${origin}/?error=checkout_failed`);
  }
}

export async function POST(request: NextRequest) {
  const origin = request.nextUrl.origin;

  if (!process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Stripe not configured" }, { status: 500 });
  }

  try {
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: "2026-02-25.clover",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: {
              name: "Postify Pro — Lifetime Access",
              description: "Content Calendar & Social Media Planner — One-time purchase",
            },
            unit_amount: 2900,
          },
          quantity: 1,
        },
      ],
      mode: "payment",
      success_url: `${origin}/app?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/`,
      metadata: {
        product: "postify_pro",
      },
    });

    return NextResponse.json({ url: session.url });
  } catch (error) {
    console.error("Stripe error:", error);
    return NextResponse.json({ error: "Failed to create checkout session" }, { status: 500 });
  }
}
