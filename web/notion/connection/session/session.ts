import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";

export type SelectedNotionDatabase = {
  id: string;
  name: string;
  titleProperty: string;
};

export type NotionSession = {
  accessToken: string;
  refreshToken: string;
  workspaceName: string;
  selectedDatabase?: SelectedNotionDatabase;
};

const VERSION = "v1";

function keyFrom(secret: string) {
  if (!secret) throw new Error("NOTION_SESSION_SECRET is missing.");
  return createHash("sha256").update(secret).digest();
}

export function sealNotionSession(session: NotionSession, secret: string) {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", keyFrom(secret), iv);
  const ciphertext = Buffer.concat([
    cipher.update(JSON.stringify(session), "utf8"),
    cipher.final(),
  ]);
  const authTag = cipher.getAuthTag();

  return [VERSION, iv, authTag, ciphertext]
    .map((part) => (typeof part === "string" ? part : part.toString("base64url")))
    .join(".");
}

export function openNotionSession(value: string, secret: string): NotionSession | null {
  try {
    const [version, iv, authTag, ciphertext] = value.split(".");
    if (version !== VERSION || !iv || !authTag || !ciphertext) return null;

    const decipher = createDecipheriv(
      "aes-256-gcm",
      keyFrom(secret),
      Buffer.from(iv, "base64url"),
    );
    decipher.setAuthTag(Buffer.from(authTag, "base64url"));
    const plaintext = Buffer.concat([
      decipher.update(Buffer.from(ciphertext, "base64url")),
      decipher.final(),
    ]).toString("utf8");
    const parsed = JSON.parse(plaintext) as NotionSession;

    if (!parsed.accessToken || !parsed.refreshToken || !parsed.workspaceName) return null;
    return parsed;
  } catch {
    return null;
  }
}
