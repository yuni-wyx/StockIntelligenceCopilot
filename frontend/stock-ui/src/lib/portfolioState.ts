import type { HoldingInput } from "./portfolioApi";

export const EMPTY_HOLDING: HoldingInput = {
  ticker: "",
  name: "",
  asset_type: "",
  category: "",
  notes: "",
};

export function appendHolding(holdings: HoldingInput[]): HoldingInput[] {
  return [...holdings, { ...EMPTY_HOLDING }];
}
