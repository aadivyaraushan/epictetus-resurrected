import { describe, expect, it } from "vitest";

import { openNotionSession, sealNotionSession, type NotionSession } from "./session";

const SESSION: NotionSession = {
  accessToken: "access-token",
  refreshToken: "refresh-token",
  workspaceName: "Evening Studio",
  selectedDatabase: {
    id: "data-source-id",
    name: "Evening Reviews",
    titleProperty: "Name",
  },
};

describe("encrypted Notion session cookie", () => {
  it("round-trips the complete connection without exposing either token", () => {
    const sealed = sealNotionSession(SESSION, "a-long-test-secret");

    expect(sealed).not.toContain(SESSION.accessToken);
    expect(sealed).not.toContain(SESSION.refreshToken);
    expect(openNotionSession(sealed, "a-long-test-secret")).toEqual(SESSION);
  });

  it("rejects a cookie changed by the browser", () => {
    const sealed = sealNotionSession(SESSION, "a-long-test-secret");
    const changed = `${sealed.slice(0, -2)}aa`;

    expect(openNotionSession(changed, "a-long-test-secret")).toBeNull();
  });

  it("rejects a cookie sealed by another deployment", () => {
    const sealed = sealNotionSession(SESSION, "first-secret");

    expect(openNotionSession(sealed, "second-secret")).toBeNull();
  });
});
