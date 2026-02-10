import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/layout/Header";
import MobileNav from "@/components/layout/MobileNav";
import { AuthProvider } from "@/contexts/AuthContext";
import QueryProvider from "@/providers/QueryProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Stock-Vis | 쉽고 간단한 포트폴리오 관리",
  description: "초보자도 쉽게 관리할 수 있는 AI 기반 포트폴리오 분석 플랫폼",
  manifest: "/manifest.json",
  themeColor: "#58A6FF",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Stock-Vis",
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
    viewportFit: "cover",
  },
  icons: {
    icon: [
      { url: "/icons/icon.svg", type: "image/svg+xml" },
    ],
    apple: [
      { url: "/icons/icon.svg", type: "image/svg+xml" },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50 dark:bg-gray-900`}
        suppressHydrationWarning
      >
        <QueryProvider>
          <AuthProvider>
            <Header />
            <main className="min-h-screen">
              {children}
            </main>
            <MobileNav />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
