import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

export async function POST(req: NextRequest) {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    return NextResponse.json({ verified: false, error: 'Stripe not configured' }, { status: 500 });
  }

  try {
    const { sessionId } = await req.json();

    if (!sessionId || typeof sessionId !== 'string') {
      return NextResponse.json({ verified: false, error: 'No session ID' }, { status: 400 });
    }

    const stripe = new Stripe(secretKey, {
      httpClient: Stripe.createFetchHttpClient(),
    });

    const session = await stripe.checkout.sessions.retrieve(sessionId);

    // Entitlement must be tied to THIS product's checkout. All OEFR products
    // share a single Stripe account, so a bare payment_status==='paid' check
    // lets any paid session_id from any product (e.g. the $14 SSDI kit) unlock
    // SubTracker for free. Require the product marker set in /api/checkout and
    // a USD payment, in addition to a completed payment.
    const isPaid = session.payment_status === 'paid';
    const isThisProduct = session.metadata?.product === 'subtracker-lifetime';
    const isUsd = session.currency === 'usd';

    if (isPaid && isThisProduct && isUsd) {
      return NextResponse.json({ verified: true });
    }

    return NextResponse.json({ verified: false, error: 'Payment not completed' }, { status: 403 });
  } catch {
    return NextResponse.json({ verified: false, error: 'Invalid session' }, { status: 403 });
  }
}
