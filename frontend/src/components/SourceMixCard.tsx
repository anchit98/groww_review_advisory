type Props = { sourceMix?: Record<string, number> };

export function SourceMixCard({ sourceMix }: Props) {
  const app = sourceMix?.app_store ?? 0;
  const play = sourceMix?.play_store ?? 0;
  const total = app + play || 1;
  const playPct = (play / total) * 100;
  const appPct = (app / total) * 100;

  return (
    <section className="glass-panel glass-panel-interactive p-4 sm:p-5">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-on-surface-variant/80">
        Source mix (analysis corpus)
      </h3>
      <div className="space-y-4 text-sm">
        <div>
          <div className="mb-2 flex justify-between text-on-surface">
            <span>Play Store</span>
            <span className="tabular-nums font-medium">{play}</span>
          </div>
          <div className="glass-progress-track">
            <div
              className="glass-progress-fill bg-primary-container text-primary-container"
              style={{ width: `${playPct}%` }}
            />
          </div>
        </div>
        <div>
          <div className="mb-2 flex justify-between text-on-surface">
            <span>App Store</span>
            <span className="tabular-nums font-medium">{app}</span>
          </div>
          <div className="glass-progress-track">
            <div
              className="glass-progress-fill bg-tertiary text-tertiary"
              style={{ width: `${appPct}%` }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
