type Props = {
  items: string[];
  className?: string;
};

export function BulletList({ items, className = "" }: Props) {
  if (!items.length) return null;

  return (
    <ul className={`space-y-1.5 text-sm leading-relaxed text-on-surface-variant/90 ${className}`}>
      {items.map((item, index) => (
        <li key={`${index}-${item.slice(0, 24)}`} className="flex gap-2">
          <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary/80" aria-hidden />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
