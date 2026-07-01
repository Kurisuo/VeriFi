import { useState } from "react";
import type { SourceCitation } from "../../api/types";

interface SourceCardProps {
  source: SourceCitation;
}

const SNIPPET_PREVIEW_LENGTH = 120;

export function SourceCard({ source }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isLong = source.text.length > SNIPPET_PREVIEW_LENGTH;
  const displayText =
    expanded || !isLong
      ? source.text
      : `${source.text.slice(0, SNIPPET_PREVIEW_LENGTH)}…`;

  return (
    <li className="source-card">
      <div className="source-card__header">
        <span className="source-card__document">{source.source_document}</span>
        <span className="source-card__meta">
          Page {source.page_number} · {Math.round(source.score * 100)}% match
        </span>
      </div>
      <p className="source-card__snippet">{displayText}</p>
      {isLong && (
        <button
          type="button"
          className="source-card__toggle"
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
      <div
        className="source-card__score-bar"
        role="presentation"
        style={{ width: `${Math.round(source.score * 100)}%` }}
      />
    </li>
  );
}
