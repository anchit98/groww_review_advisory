import { splitIntoLines } from "../lib/format";
import { cn } from "../lib/cn";

const LINE_LEADING = "leading-[1.375rem]";

type FixedTextProps = {
  text: string;
  lineCount: number;
  as?: "h3" | "p" | "div";
  className?: string;
};

/** Renders prose split into a fixed number of lines with reserved height (for grid alignment). */
export function CardFixedLines({ text, lineCount, as: Tag = "p", className }: FixedTextProps) {
  const lines = splitIntoLines(text, lineCount);

  return (
    <Tag
      className={cn(LINE_LEADING, className)}
      style={{ minHeight: `${lineCount * 1.375}rem` }}
      title={text}
    >
      {lines.map((line, index) => (
        <span key={index} className="block">
          {line || "\u00A0"}
        </span>
      ))}
    </Tag>
  );
}

type FixedListProps = {
  items: string[];
  lineCount: number;
  className?: string;
  itemClassName?: string;
};

function padLines(items: string[], lineCount: number): string[] {
  const rows = items.slice(0, lineCount).map((line) => line.trim());
  while (rows.length < lineCount) {
    rows.push("");
  }
  return rows;
}

const INSIGHT_ROW_HEIGHT_REM = 2.25;

/** Renders a fixed number of insight rows with equal height per row. */
export function CardFixedLineList({ items, lineCount, className, itemClassName }: FixedListProps) {
  const rows = padLines(items, lineCount);

  return (
    <ul
      className={cn("space-y-1.5", className)}
      style={{ minHeight: `${lineCount * INSIGHT_ROW_HEIGHT_REM}rem` }}
    >
      {rows.map((line, index) => (
        <li
          key={index}
          title={line || undefined}
          className={cn(
            "glass-inset flex items-center rounded-lg px-2.5 py-1 text-xs font-medium",
            LINE_LEADING,
            !line && "opacity-0",
            itemClassName,
          )}
          style={{ minHeight: `${INSIGHT_ROW_HEIGHT_REM}rem` }}
        >
          {line || "\u00A0"}
        </li>
      ))}
    </ul>
  );
}
