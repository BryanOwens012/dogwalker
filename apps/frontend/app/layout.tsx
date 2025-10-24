import type React from "react";
import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

export const metadata: Metadata = {
  title: {
    default:
      "🐕 Dogwalker - Slack Bot That Turns Feature Requests Into Pull Requests",
    template: "%s | Dogwalker",
  },
  description: "Slack bot that turns feature requests into pull requests.",
  keywords: [
    "AI coding",
    "automation",
    "Slack bot",
    "pull requests",
    "Claude AI",
    "code generation",
    "multi-agent",
    "DevOps",
    "CI/CD",
  ],
  authors: [{ name: "Bryan Owens" }],
  creator: "Bryan Owens",
  publisher: "Bryan Owens",
};

const RootLayout = ({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) => {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
};

export default RootLayout;
