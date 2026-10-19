import { StreamPermission, StreamrClient } from "@streamr/sdk";

import type { StreamGateway } from "./gateway.js";

/**
 * Live client for @streamr/sdk 103.4.0.
 *
 * Checked against that version's exported types and package README:
 * - `new StreamrClient({ auth: { privateKey } })` uses DEFAULT_KEY_TYPE
 *   `ECDSA_SECP256K1_EVM`, so the value is an Ethereum private key.
 * - `getOrCreateStream({ id })` returns a Stream.
 * - `stream.publish(content)` publishes one JSON message.
 * - `grantPermissions(streamId, { public: true, permissions: [SUBSCRIBE] })`
 *   sets public subscribe.
 * - `destroy()` shuts the client down.
 *
 * Creating a stream and changing permissions are Polygon transactions and
 * need POL for gas. Publishing a message to a stream that already exists
 * is a Streamr network publish, not a second permission transaction.
 * Docs: https://docs.streamr.network/usage/sdk/api/
 */
export async function createStreamGateway(privateKey: string): Promise<StreamGateway> {
  const client = new StreamrClient({
    auth: { privateKey },
  });
  return {
    async getOrCreateStream(props) {
      const stream = await client.getOrCreateStream(props);
      return {
        id: stream.id,
        publish: (content) => stream.publish(content),
      };
    },
    async grantPublicSubscribe(streamId) {
      await client.grantPermissions(streamId, {
        public: true,
        permissions: [StreamPermission.SUBSCRIBE],
      });
    },
    async destroy() {
      await client.destroy();
    },
  };
}
