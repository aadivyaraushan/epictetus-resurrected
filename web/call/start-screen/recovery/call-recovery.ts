export type CallFailureStage = "admission" | "room";

export function callRecoveryMessage(stage: CallFailureStage, _error: unknown): string {
  if (stage === "room") {
    return "The call could not connect. Check microphone access, then try again.";
  }
  return "The call could not start. Please try again.";
}
