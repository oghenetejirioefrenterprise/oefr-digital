export const dynamic = "force-static";

export function GET() {
  const body = [
    "User-agent: *",
    "Allow: /",
    "Sitemap: https://data.oefrenterprise.com/sitemap.xml"
  ].join("\n");
  return new Response(body, {
    headers: { "Content-Type": "text/plain" }
  });
}
