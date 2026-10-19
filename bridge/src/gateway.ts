/** Narrow gateway so tests can mock Streamr without loading @streamr/sdk. */

export interface PublishableStream {
  id: string;
  publish(content: unknown): Promise<unknown>;
}

export interface StreamGateway {
  getOrCreateStream(props: { id: string }): Promise<PublishableStream>;
  grantPublicSubscribe(streamId: string): Promise<void>;
  destroy(): Promise<void>;
}
