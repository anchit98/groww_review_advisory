import { ActionHeadline } from "./ActionHeadline";

type ActionItem = {
  action: string;
};

type Props = {
  items: ActionItem[];
};

export function ActionItemsList({ items }: Props) {
  if (!items.length) return null;

  return (
    <div className="glass-panel divide-y divide-white/8 overflow-hidden">
      {items.map((item, index) => (
        <div
          key={`${index}-${item.action.slice(0, 24)}`}
          className="flex items-start gap-3 p-4 sm:gap-4 sm:p-5"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-primary/30 bg-primary/15 text-sm font-bold tabular-nums text-primary">
            {index + 1}
          </span>
          <ActionHeadline text={item.action.trim()} />
        </div>
      ))}
    </div>
  );
}
