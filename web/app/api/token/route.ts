/**
 * Mint the token that lets a browser into a room with Epictetus.
 *
 * Input:  POST (the body is ignored)
 * Output: { serverUrl, token, roomName }
 *
 * Steps:
 *   1. Make a fresh room name, so two callers never land in each other's call.
 *   2. Sign a token restricted to that room.
 *   3. Ask LiveKit to dispatch the "epictetus" worker into that room.
 *
 * This exists because the LiveKit API secret can sign a token for any room and
 * any permission. It has to stay on a server. The browser gets a token scoped to
 * one room and nothing else.
 *
 * Notion credentials live in an encrypted HttpOnly browser cookie and never
 * enter LiveKit participant metadata.
 */

import { RoomAgentDispatch, RoomConfiguration } from "@livekit/protocol";
import { AccessToken } from "livekit-server-sdk";
import { NextResponse } from "next/server";

import { setReviewPermit } from "../../../review/draft/access/review-access-cookie";

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

export async function POST(_request: Request) {
  const url = process.env.LIVEKIT_URL;
  const key = process.env.LIVEKIT_API_KEY;
  const secret = process.env.LIVEKIT_API_SECRET;
  const reviewSecret = process.env.REVIEW_SESSION_SECRET;

  if (!url || !key || !secret || !reviewSecret) {
    // Named individually: a half-configured deployment is the likeliest cause of
    // this, and "one of three things is missing" wastes someone's evening.
    const missing = [
      !url && "LIVEKIT_URL",
      !key && "LIVEKIT_API_KEY",
      !secret && "LIVEKIT_API_SECRET",
      !reviewSecret && "REVIEW_SESSION_SECRET",
    ].filter(Boolean);
    console.error(`[api.token] cannot mint a token; missing ${missing.join(", ")}`);
    return NextResponse.json(
      { error: `Server is missing ${missing.join(", ")}.` },
      { status: 500 },
    );
  }

  const roomName = `epictetus-${crypto.randomUUID()}`;
  const identity = `caller-${crypto.randomUUID().slice(0, 8)}`;

  const at = new AccessToken(key, secret, {
    identity,
    name: "caller",
    ttl: TOKEN_TTL,
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

  console.log(`[api.token] room ${roomName} for ${identity}`);

  const response = NextResponse.json({
    serverUrl: url,
    token: await at.toJwt(),
    roomName,
    proof: {
      roomName,
      lifetime: "30 minutes",
      agentName: AGENT_NAME,
      permissions: ["join this room", "publish microphone and data", "subscribe"],
    },
  });
  setReviewPermit(response);
  return response;
}
