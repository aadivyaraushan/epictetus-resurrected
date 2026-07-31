import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@livekit/components-styles";
import "./globals.css";

export const metadata: Metadata = {
  title: "Epictetus, Resurrected",
  description:
    "A spoken conversation with Epictetus, grounded in his Discourses. Every answer he gives is checked against the text, and the passages he drew on are shown as he speaks.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
