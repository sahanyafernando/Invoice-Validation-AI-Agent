import "./globals.css";

export const metadata = {
  title: "InvoiceGuard AI",
  description: "Explainable invoice validation agent",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}