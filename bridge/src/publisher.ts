import type { StreamGateway } from "./gateway.js";
import type { TelemetryMessage } from "./schema.js";

export interface Publisher {
  publish(streamId: string, message: TelemetryMessage): Promise<void>;
}

export class DryRunPublisher implements Publisher {
  constructor(private readonly write: (line: string) => void) {}

  async publish(streamId: string, message: TelemetryMessage): Promise<void> {
    this.write(
      JSON.stringify({
        event: "dry-run",
        published: false,
        streamId,
        message,
      }),
    );
  }
}

/**
 * Publishes only messages the license gate has already marked publishable.
 * The first call for a stream id uses getOrCreateStream, which creates the
 * stream on Polygon when it does not already exist.
 */
export class GatewayPublisher implements Publisher {
  private readonly streams = new Map<string, { publish(content: unknown): Promise<unknown> }>();

  constructor(private readonly gateway: StreamGateway) {}

  async publish(streamId: string, message: TelemetryMessage): Promise<void> {
    if (!message.publishable || message.sample) {
      throw new Error("Refusing to publish a sample or license-blocked message.");
    }
    let stream = this.streams.get(streamId);
    if (!stream) {
      stream = await this.gateway.getOrCreateStream({ id: streamId });
      this.streams.set(streamId, stream);
    }
    await stream.publish(message);
  }
}
