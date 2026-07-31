import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { StartScreen } from "./start-screen";

const commonProps = {
  onStart: () => undefined,
  connecting: false,
  callFailure: null,
  notionFailure: null,
  notionBusy: false,
  onDisconnectNotion: () => undefined,
};

describe("single Notion review database", () => {
  it("shows the bound database without a chooser", () => {
    const html = renderToStaticMarkup(
      <StartScreen
        {...commonProps}
        notion={{
          connected: true,
          workspaceName: "My Workspace",
          selectedDatabase: { id: "reviews", name: "Evening Reviews", titleProperty: "Name" },
        }}
      />,
    );

    expect(html).toContain("Evening Reviews");
    expect(html).not.toContain("<select");
    expect(html).not.toContain("Choose a database");
  });

  it("shows a reconnect action when the database count was rejected", () => {
    const html = renderToStaticMarkup(
      <StartScreen
        {...commonProps}
        notion={{
          connected: false,
          reconnectMessage:
            "More than one database was shared. Reconnect and choose only the Evening Reviews database.",
        }}
      />,
    );

    expect(html).toContain("Reconnect Notion");
    expect(html).toContain("choose only the Evening Reviews database");
    expect(html).not.toContain("<select");
  });
});
