import type { TelemetryMessage } from "../schema.js";
import type { StreamPath } from "../streams.js";

export interface SourceAdapter {
  id: string;
  stream: StreamPath;
  status: "implemented" | "stub" | "sample";
  /** Shown in logs. Stubs must say they are not fetching a network. */
  note: string;
  poll(): Promise<TelemetryMessage[]>;
}
