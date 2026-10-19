import type { SourceAdapter } from "./types.js";

/**
 * M2 placeholders. `poll` returns no messages. None of these call a network.
 * GEODNET is station health only: RTK corrections are not a field and must
 * not be added to this stub.
 */
export const STUBS: readonly SourceAdapter[] = [
  {
    id: "geodnet",
    stream: "fleet/geodnet-status",
    status: "stub",
    note: "M2 stub. Station health only. No RTK correction data is fetched or representable here.",
    poll: async () => [],
  },
  {
    id: "wingbits",
    stream: "fleet/wingbits",
    status: "stub",
    note: "M2 stub. No Wingbits API is called and no flight positions are invented.",
    poll: async () => [],
  },
  {
    id: "helium",
    stream: "fleet/helium",
    status: "stub",
    note: "M2 stub. No Helium hotspot or reward data is fetched.",
    poll: async () => [],
  },
  {
    id: "air-quality",
    stream: "beltline/air-quality",
    status: "stub",
    note: "M2 stub. No co-located air-quality sensor is installed. Intended license, once collected by this project, is CC BY 4.0, separate from WeatherXM.",
    poll: async () => [],
  },
];

export function stubById(id: string): SourceAdapter | undefined {
  return STUBS.find((adapter) => adapter.id === id);
}
