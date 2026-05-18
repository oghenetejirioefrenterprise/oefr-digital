export function BonusStack({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
        What's included
      </h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-base">
            <span aria-hidden className="mt-1.5 size-1.5 shrink-0 rounded-full bg-neutral-900" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
