import { Lightbulb } from "lucide-react";

import { resolveBulletPoints } from "../lib/bullets";
import { shortActionTitle } from "../lib/format";
import { BulletList } from "./BulletList";

type Props = {
  title: string;
  body: string;
  bulletPoints?: string[];
  linkedTheme: string;
};

export function InsightCard({ title, body, bulletPoints, linkedTheme }: Props) {
  const bullets = resolveBulletPoints(bulletPoints, body);

  return (
    <article className="glass-panel glass-panel-interactive p-5">
      <div className="mb-3 flex items-center gap-3">
        <span className="glass-icon-well !text-primary">
          <Lightbulb className="h-4 w-4" aria-hidden />
        </span>
        <h3 className="font-semibold tracking-tight text-on-surface">
          {shortActionTitle(title, 72)}
        </h3>
      </div>
      <p className="mb-3 text-sm font-medium text-on-surface/95">{shortActionTitle(body, 120)}</p>
      <BulletList items={bullets} />
      <p className="mt-3 text-xs text-on-surface-variant/70">Linked theme: {linkedTheme}</p>
    </article>
  );
}
