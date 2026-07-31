import { NextResponse } from "next/server";

import { createReviewPermit, verifyReviewPermit } from "./review-access";

const COOKIE = "review_permit";
const OPTIONS = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
};

function cookieValue(request: Request) {
  const cookies = request.headers.get("cookie") ?? "";
  const item = cookies.split(";").find((part) => part.trim().startsWith(`${COOKIE}=`));
  return item ? decodeURIComponent(item.trim().slice(COOKIE.length + 1)) : "";
}

export function setReviewPermit(response: NextResponse) {
  const secret = process.env.REVIEW_SESSION_SECRET ?? "";
  response.cookies.set({
    name: COOKIE,
    value: createReviewPermit(secret),
    ...OPTIONS,
    maxAge: 30 * 60,
  });
}

export function hasReviewPermit(request: Request) {
  return verifyReviewPermit(
    cookieValue(request),
    process.env.REVIEW_SESSION_SECRET ?? "",
  );
}

export function clearReviewPermit(response: NextResponse) {
  response.cookies.set({ name: COOKIE, value: "", ...OPTIONS, maxAge: 0 });
}
