export default function handler(req, res) {
  res.setHeader(
    "Set-Cookie",
    "session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
  );
  res.status(200).json({ ok: true });
}
