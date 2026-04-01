"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function ExplainPage() {
  return (
    <Suspense fallback={null}>
      <ExplainRedirect />
    </Suspense>
  );
}

function ExplainRedirect() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const ticker = params.get("ticker") ?? "";
    const next = ticker
      ? `/copilot?mode=explain&ticker=${encodeURIComponent(ticker)}`
      : "/copilot?mode=explain";
    router.replace(next);
  }, [params, router]);

  return null;
}
