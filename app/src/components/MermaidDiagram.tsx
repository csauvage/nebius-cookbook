"use client";

import { useEffect, useId, useState } from "react";

interface MermaidDiagramProps {
  source: string;
}

export function MermaidDiagram({ source }: MermaidDiagramProps) {
  const reactId = useId();
  const diagramId = `mermaid-${reactId.replace(/:/g, "")}`;
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function renderDiagram() {
      try {
        const { default: mermaid } = await import("mermaid");
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "base",
          themeVariables: {
            background: "transparent",
            fontSize: "22px",
            primaryColor: "#f8f4ec",
            primaryBorderColor: "#7c5cff",
            primaryTextColor: "#181512",
            lineColor: "#7c5cff",
            textColor: "#181512",
            fontFamily: "IBM Plex Sans, system-ui, sans-serif",
          },
        });

        const result = await mermaid.render(diagramId, source);
        if (!cancelled) {
          setSvg(result.svg);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setSvg(null);
          setError(err instanceof Error ? err.message : "Unable to render Mermaid diagram.");
        }
      }
    }

    void renderDiagram();

    return () => {
      cancelled = true;
    };
  }, [diagramId, source]);

  if (error) {
    return (
      <pre className="thin-scroll my-6 overflow-x-auto border border-edge-strong bg-surface/60 p-4 font-mono text-[13px] leading-relaxed text-ink">
        <code>{source}</code>
      </pre>
    );
  }

  return (
    <figure className="my-8 overflow-x-auto border border-edge bg-surface/40 p-4">
      {svg ? (
        <div
          className="min-w-[920px] [&_svg]:h-auto [&_svg]:w-full [&_svg]:max-w-none [&_svg_text]:text-[22px]"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : (
        <div className="font-mono text-xs uppercase tracking-[0.16em] text-ink-dim">
          Rendering diagram
        </div>
      )}
    </figure>
  );
}
