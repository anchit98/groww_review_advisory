import { cn } from "../lib/cn";

type Props = {
  items: string[];
  chipClassName?: string;
};

export function InsightPills({ items, chipClassName = "" }: Props) {
  if (!items.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <span
          key={`${index}-${item.slice(0, 16)}`}
          title={item}
          className={cn(
            "glass-inset rounded-lg px-2.5 py-1.5 text-xs font-medium leading-snug",
            chipClassName,
          )}
        >
          {item}
        </span>
      ))}
    </div>
  );
}
