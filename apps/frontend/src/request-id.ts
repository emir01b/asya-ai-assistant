// getRandomValues is available on LAN HTTP as well as HTTPS/localhost.
export function requestId(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}
