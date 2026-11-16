import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClipView — AI Video Studio",
  description: "Transforme vídeos longos em clipes curtos."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
