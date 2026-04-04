import { ImageResponse } from "next/og";

export const alt = "Recover Revenue Hiding in Your CRM — OEFR Digital";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          width: "100%",
          height: "100%",
          backgroundColor: "#0f172a",
          padding: "60px 80px",
        }}
      >
        {/* Top: OEFR Digital label */}
        <div
          style={{
            display: "flex",
            fontSize: 22,
            fontWeight: 700,
            color: "#3b82f6",
            letterSpacing: "0.05em",
          }}
        >
          OEFR DIGITAL
        </div>

        {/* Center: Headline + subtext */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              fontSize: 64,
              fontWeight: 800,
              color: "#ffffff",
              lineHeight: 1.2,
              marginBottom: 24,
            }}
          >
            Recover Revenue Hiding in Your CRM
          </div>
          <div
            style={{
              fontSize: 26,
              color: "#94a3b8",
              lineHeight: 1.5,
            }}
          >
            Done-for-you email reactivation. No ads needed.
          </div>
        </div>

        {/* Bottom right: Pricing */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <div
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: "#e2e8f0",
            }}
          >
            $750 setup + $300/mo
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
