import { useEffect } from "react";
import Head from "next/head";
import "../styles/globals.css";

export default function App({ Component, pageProps }) {
  useEffect(() => {
    const orig = window.fetch;
    window.fetch = async function (...args) {
      const res = await orig.apply(this, args);
      if (res.status === 401) {
        res.clone().json().then(data => {
          if (data.detail === "session_expired") window.location.href = "/login";
        }).catch(() => {});
      }
      return res;
    };
    return () => { window.fetch = orig; };
  }, []);

  return (
    <>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/logo.webp" type="image/webp" />
      </Head>
      <Component {...pageProps} />
    </>
  );
}
