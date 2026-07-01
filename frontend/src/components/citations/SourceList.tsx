import type { SourceCitation } from "../../api/types";
import { SourceCard } from "./SourceCard";

interface SourceListProps {
  sources: SourceCitation[];
}

export function SourceList({ sources }: SourceListProps) {
  if (sources.length === 0) {
    return (
      <p className="source-list source-list--empty">
        No matching source passages were retrieved.
      </p>
    );
  }

  return (
    <div className="source-list">
      <p className="source-list__heading">Sources</p>
      <ul className="source-list__items">
        {sources.map((source, index) => (
          <SourceCard key={`${source.source_document}-${source.page_number}-${index}`} source={source} />
        ))}
      </ul>
    </div>
  );
}
