import { describe, expect, it } from "vitest";

import { callRecoveryMessage } from "./call-recovery";

describe("call failure recovery copy", () => {
  it("turns room and microphone transport failures into one useful next step", () => {
    const technical = new Error(
      "could not establish signal connection: Abort handler called",
    );

    expect(callRecoveryMessage("room", technical)).toBe(
      "The call could not connect. Check microphone access, then try again.",
    );
    expect(callRecoveryMessage("room", new DOMException("Not supported", "NotSupportedError")))
      .toBe("The call could not connect. Check microphone access, then try again.");
    expect(callRecoveryMessage("room", technical)).not.toContain("Abort handler");
  });

  it("keeps admission failures short and recoverable", () => {
    expect(callRecoveryMessage("admission", new Error("Token request failed (500).")))
      .toBe("The call could not start. Please try again.");
  });
});
