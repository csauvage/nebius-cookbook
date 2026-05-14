import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, Jersey_15 } from "next/font/google";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

const jersey = Jersey_15({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display-jersey",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Nebius Cookbook",
    template: "%s — Nebius Cookbook",
  },
  description: "Production-grade recipes for building AI agents on Nebius AgentKit.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://cookbook.nebius.com"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${plexMono.variable} ${jersey.variable}`}
    >
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
