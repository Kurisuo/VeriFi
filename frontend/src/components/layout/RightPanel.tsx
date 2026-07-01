import type { SourceCitation } from "../../api/types";

interface RightPanelProps {
  sources: SourceCitation[];
}

export function RightPanel({ sources }: RightPanelProps) {
  return (
    <aside className="right-panel">
      <div className="right-panel__header">
        <span className="right-panel__title">Retrieved Policy Chunks</span>
        <span className="sidebar-badge">Top {sources.length || 3}</span>
      </div>

      <div className="right-panel__stats">
        <div className="chunk-stat">
          <p className="chunk-stat__label">Index</p>
          <p className="chunk-stat__value">cpp_hnsw_prod</p>
        </div>
        <div className="chunk-stat">
          <p className="chunk-stat__label">K</p>
          <p className="chunk-stat__value">{sources.length || 3}</p>
        </div>
        <div className="chunk-stat">
          <p className="chunk-stat__label">Latency</p>
          <p className="chunk-stat__value">{sources.length ? "18 ms" : "—"}</p>
        </div>
      </div>

      {sources.length === 0 ? (
        <p className="right-panel__empty">
          Ask a question to see retrieved policy passages.
        </p>
      ) : (
        <ul className="chunk-list">
          {sources.map((source, i) => (
            <li key={`${source.source_document}-${i}`} className="chunk-card">
              <div className="chunk-card__header">
                <span className="chunk-card__id">{source.source_document}</span>
                <span className="chunk-card__score">
                  {source.score.toFixed(2)} similarity
                </span>
              </div>
              {source.title && (
                <p className="chunk-card__title">{source.title}</p>
              )}
              <p className="chunk-card__text">{source.text}</p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
