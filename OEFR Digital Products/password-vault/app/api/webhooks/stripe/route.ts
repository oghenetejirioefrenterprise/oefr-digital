import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { Resend } from "resend";

export async function POST(req: NextRequest) {
  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
    apiVersion: "2026-02-25.clover",
  });
  const resend = new Resend(process.env.RESEND_API_KEY);
  const sig = req.headers.get("stripe-signature");
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!sig || !webhookSecret) {
    return NextResponse.json({ error: "Webhook configuration error" }, { status: 400 });
  }

  let event: Stripe.Event;
  try {
    const rawBody = await req.text();
    event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Webhook verification failed";
    return NextResponse.json({ error: message }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const customerEmail = session.customer_details?.email ?? session.customer_email;
    const productName = session.metadata?.productName || "Password Vault";
    const appUrl = (process.env.NEXT_PUBLIC_APP_URL || "https://password-vault.vercel.app").replace(/\/$/, "");

    if (customerEmail) {
      try {
        await resend.emails.send({
          from: "noreply@oefrenterprise.com",
          to: customerEmail,
          subject: `Your ${productName} Purchase Confirmation`,
          html: buildEmailHtml(productName, appUrl),
          text: buildEmailText(productName, appUrl),
        });
      } catch (emailErr) {
        console.error("Email send error:", emailErr);
      }
    }
  }

  return NextResponse.json({ received: true });
}

function buildEmailHtml(productName: string, appUrl: string): string {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0a0f1e;font-family:'Segoe UI',Tahoma,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0f1e;padding:40px 20px;"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#0d1526;border-radius:12px;border:1px solid #1e3a5f;max-width:600px;">
<tr><td style="background:linear-gradient(135deg,#0a0f1e,#0d2137);padding:32px 40px;border-bottom:1px solid #1e3a5f;">
<h1 style="margin:0;font-size:24px;color:#22d3ee;">${productName}</h1>
<p style="margin:6px 0 0;font-size:12px;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;">by OEfr Enterprise</p>
</td></tr>
<tr><td style="padding:40px;">
<h2 style="margin:0 0 16px;font-size:22px;color:#f1f5f9;">Thank you for your purchase!</h2>
<p style="margin:0 0 24px;font-size:15px;color:#94a3b8;line-height:1.7;">Your payment was successful. You now have full access to <strong style="color:#f1f5f9;">${productName}</strong>.</p>
<table cellpadding="0" cellspacing="0"><tr>
<td style="border-radius:8px;background:linear-gradient(135deg,#0891b2,#0e7490);">
<a href="${appUrl}" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:600;color:#fff;text-decoration:none;border-radius:8px;">Open ${productName}</a>
</td></tr></table>
<p style="margin:32px 0 0;font-size:13px;color:#64748b;line-height:1.7;">Bookmark this link for easy access: <a href="${appUrl}" style="color:#22d3ee;">${appUrl}</a></p>
</td></tr>
<tr><td style="background:#080c18;padding:24px 40px;border-top:1px solid #1e3a5f;">
<p style="margin:0;font-size:12px;color:#475569;text-align:center;">&copy; ${new Date().getFullYear()} OEfr Enterprise &middot; Questions? Reply to this email.</p>
</td></tr></table></td></tr></table></body></html>`;
}

function buildEmailText(productName: string, appUrl: string): string {
  return `Thank you for your purchase!\n\nYou now have full access to ${productName}.\n\nAccess your app: ${appUrl}\n\nQuestions? Reply to this email.\n\n© ${new Date().getFullYear()} OEfr Enterprise`;
}
