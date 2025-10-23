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
    default: "Dogwalker - Multi-Agent AI Coding System",
    template: "%s | Dogwalker",
  },
  description:
    "Open-source, self-hosted AI coding system that turns Slack messages into production-ready pull requests. Multiple AI agents work in parallel, write tests, and deliver code ready for human review.",
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
  authors: [{ name: "Dogwalker Contributors" }],
  creator: "Dogwalker",
  publisher: "Dogwalker",
};

const RootLayout = ({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) => {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  );
};

export default RootLayout;
