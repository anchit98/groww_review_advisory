import { CardFixedLines } from "./CardFixedLines";
import { ACTION_ITEM_HEADLINE_LINES } from "../lib/themesPageLayout";

type Props = {
  text: string;
};

/** Fixed two-line headline so playbook cards align in the grid. */
export function ActionHeadline({ text }: Props) {
  return (
    <CardFixedLines
      as="h3"
      text={text}
      lineCount={ACTION_ITEM_HEADLINE_LINES}
      className="text-base font-semibold text-on-surface"
    />
  );
}
