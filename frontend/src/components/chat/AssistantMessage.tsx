import type { SourceCitation } from "../../api/types";

interface AssistantMessageProps {
  content: string;
  sources: SourceCitation[];
}

export function AssistantMessage({ content, sources }: AssistantMessageProps) {
  return (
    <div className="message message--assistant">
      <span className="message__avatar message__avatar--fa">FA</span>
      <div className="message__body">
        <p className="message__text">{content}</p>
        {sources.length > 0 && (
          <div className="citation-chips">
            {sources.map((source, i) => (
              <span
                key={`${source.source_document}-${i}`}
                className="citation-chip"
              >
                {source.source_document}
                {source.section ? ` ${source.section}` : source.page_number ? ` §${source.page_number}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
