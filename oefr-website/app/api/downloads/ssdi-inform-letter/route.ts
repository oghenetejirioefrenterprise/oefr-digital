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
