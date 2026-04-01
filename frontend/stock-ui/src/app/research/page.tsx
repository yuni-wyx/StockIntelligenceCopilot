"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function ResearchPage() {
  return (
    <Suspense fallback={null}>
      <ResearchRedirect />
    </Suspense>
  );
}

function ResearchRedirect() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const ticker = params.get("ticker") ?? "";
    const next = ticker
      ? `/copilot?mode=research&ticker=${encodeURIComponent(ticker)}`
      : "/copilot?mode=research";
    router.replace(next);
  }, [params, router]);

  return null;
}
