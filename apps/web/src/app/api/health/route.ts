import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    status: "ok",
    service: "cyberai-web",
    timestamp: new Date().toISOString(),
  });
}
