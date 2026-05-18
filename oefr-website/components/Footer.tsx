import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-[#f4efe6] border-t border-[#d8cdb8]">
      <div className="mx-auto max-w-[1440px] px-6 sm:px-10 lg:px-16 pt-24 pb-12 grid gap-16 md:grid-cols-[2fr_1fr_1fr_1fr]">
        <div>
          <div className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-[#1a1713] text-[#f4efe6] italic font-[family-name:var(--font-fraunces)] text-lg mb-5">
            od
          </div>
          <p className="font-[family-name:var(--font-fraunces)] text-xl leading-snug max-w-[380px] text-[#1a1713]">
            Smart digital tools, built by engineers, priced for everyone. One-time purchase, forever yours.
          </p>
        </div>

        <FooterColumn
          title="Catalog"
          links={[
            ["/#products", "Finance & Productivity"],
            ["/#products", "Career & Business"],
            ["/#products", "IT & Engineering"],
            ["/#products", "Coming Soon"],
          ]}
        />
        <FooterColumn
          title="Studio"
          links={[
            ["/about", "About"],
            ["/blog", "Journal"],
            ["/tools", "Calculators"],
            ["/contact", "Contact"],
          ]}
        />
        <FooterColumn
          title="Terms"
          links={[
            ["/refund", "Refund policy"],
            ["/privacy", "Privacy"],
            ["/terms", "Terms of use"],
            ["/reactivation", "DB Reactivation"],
          ]}
        />
      </div>

      <div className="mx-6 sm:mx-10 lg:mx-16 border-t border-[#d8cdb8] pt-6 pb-10 flex flex-col sm:flex-row justify-between gap-3 font-[family-name:var(--font-mono)] text-[11px] tracking-[0.14em] uppercase text-[#7a6f5c]">
        <span>© 2026 OEFR Digital · All rights reserved</span>
        <span>
          <a href="mailto:info@oefrenterprise.com" className="hover:text-[#a66a2c] transition-colors">
            info@oefrenterprise.com
          </a>
        </span>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: [string, string][] }) {
  return (
    <div>
      <h4 className="font-[family-name:var(--font-mono)] text-[11px] tracking-[0.22em] uppercase text-[#7a6f5c] mb-5 font-normal">
        {title}
      </h4>
      <ul className="space-y-3">
        {links.map(([href, label]) => (
          <li key={label}>
            <Link href={href} className="text-[15px] text-[#1a1713] hover:text-[#a66a2c] transition-colors">
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
