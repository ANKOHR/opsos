import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpsOS | AI operations command center",
  description: "Auditable, human-supervised business workflows.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

