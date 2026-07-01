import { useHealth } from "../../hooks/useHealth";

export function ConnectionStatus() {
  const { isLoading, isError, data } = useHealth();

  if (isLoading) {
    return <span className="connection-status connection-status--loading">Connecting…</span>;
  }

  if (isError) {
    return (
      <span className="connection-status connection-status--error">
        Backend unavailable
      </span>
    );
  }

  return (
    <span
      className={`connection-status connection-status--${data?.status ?? "ok"}`}
    >
      {data?.status === "degraded" ? "Backend degraded" : "Backend connected"}
    </span>
  );
}
