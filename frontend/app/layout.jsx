import "./globals.css";
import Nav from "../components/Nav";

export const metadata = {
  title: "HorseEdge Analytics",
  description: "Horse racing analytics MVP with live-data provider hooks"
};

export default function RootLayout({children}) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
