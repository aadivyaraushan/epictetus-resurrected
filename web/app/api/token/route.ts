/**
 * Mint the token that lets a browser into a room with Epictetus.
 *
 * Input:  POST with an optional { passphrase } in the body
 * Output: { serverUrl, token, roomName, backend }
 *
 * Steps:
 *   1. Check the passphrase against the server's secret (see backend-choice.ts).
 *   2. Make a fresh room name, so two callers never land in each other's call.
 *   3. Sign a token that carries the verdict as participant metadata.
 *   4. Ask LiveKit to dispatch the "epictetus" worker into that room.
 *
 * This exists because the LiveKit API secret can sign a token for any room and
 * any permission. It has to stay on a server. The browser gets a token scoped to
 * one room and nothing else.
 *
 * The passphrase verdict is decided here rather than in the browser for the same
 * reason: metadata inside a signed token is something the worker can trust,
 * whereas anything the browser sends it directly is just a claim.
 */

import { RoomAgentDispatch, RoomConfiguration } from "@livekit/protocol";
import { AccessToken } from "livekit-server-sdk";
import { NextResponse } from "next/server";

import { chooseBackend } from "../../../call/access/backend-choice";

// node:crypto and the server SDK need the Node runtime, not the edge one.
export const runtime = "nodejs";
// Every call needs its own room, so nothing about this response is cacheable.
export const dynamic = "force-dynamic";

// Must match the name the worker registers under, in agent/main.py. With a name
// set, LiveKit only dispatches the worker when a token asks for it by name --
// which means a stray room cannot pull the agent in.
const AGENT_NAME = "epictetus";

// Long enough for a conversation, short enough that a leaked token is not a
// standing invitation.
const TOKEN_TTL = "30m";

export async function POST(request: Request) {
  const url = process.env.LIVEKIT_URL;
  const key = process.env.LIVEKIT_API_KEY;
  const secret = process.env.LIVEKIT_API_SECRET;

  if (!url || !key || !secret) {
    // Named individually: a half-configured deployment is the likeliest cause of
    // this, and "one of three things is missing" wastes someone's evening.
    const missing = [
      !url && "LIVEKIT_URL",
      !key && "LIVEKIT_API_KEY",
      !secret && "LIVEKIT_API_SECRET",
    ].filter(Boolean);
    console.error(`[api.token] cannot mint a token; missing ${missing.join(", ")}`);
    return NextResponse.json(
      { error: `Server is missing ${missing.join(", ")}.` },
      { status: 500 },
    );
  }

  // A caller can post anything, including nothing at all.
  let passphrase: string | undefined;
  try {
    const body = await request.json();
    passphrase = body?.passphrase;
  } catch {
    passphrase = undefined;
  }

  const backend = chooseBackend(passphrase, process.env.LIVE_BACKEND_PASSPHRASE);
  const roomName = `epictetus-${crypto.randomUUID()}`;
  const identity = `caller-${crypto.randomUUID().slice(0, 8)}`;

  const at = new AccessToken(key, secret, {
    identity,
    name: "caller",
    ttl: TOKEN_TTL,
    // The worker reads this and picks its tool backend. Signed, so the caller
    // cannot rewrite it after the fact.
    metadata: JSON.stringify({ life_backend: backend }),
  });

  at.addGrant({
    room: roomName,
    roomJoin: true,
    canPublish: true, // their microphone
    canSubscribe: true, // his voice, and the source panel data
    canPublishData: true,
  });

  at.roomConfig = new RoomConfiguration({
    agents: [new RoomAgentDispatch({ agentName: AGENT_NAME })],
  });

  // Log the verdict but never the passphrase.
  console.log(`[api.token] room ${roomName} for ${identity}, ${backend} backend`);

  return NextResponse.json({
    serverUrl: url,
    token: await at.toJwt(),
    roomName,
    backend,
  });
}
