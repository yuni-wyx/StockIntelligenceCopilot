import "./globals.css";
import { LanguageProvider } from "@/context/LanguageContext";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Stock Intelligence Copilot",
  description: "AI-powered stock research, explain, and trade analysis copilot.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
