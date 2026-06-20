import { type HTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "bone" | "ink" | "oxblood" | "outline";
  children: ReactNode;
}

const variantClass = {
  bone: "bg-bone-50 border border-ink/10",
  ink: "bg-ink text-bone border border-ink",
  oxblood: "bg-oxblood text-bone border border-oxblood-500",
  outline: "bg-transparent border border-ink",
};

export function Panel({ variant = "bone", className, children, ...rest }: PanelProps) {
  return (
    <div className={cn(variantClass[variant], className)} {...rest}>
      {children}
    </div>
  );
}

interface PanelHeaderProps {
  eyebrow?: ReactNode;
  title?: ReactNode;
  right?: ReactNode;
}

export function PanelHeader({ eyebrow, title, right }: PanelHeaderProps) {
  return (
    <div className="flex items-end justify-between px-6 pt-5 pb-4">
      <div>
        {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
        <div className="font-display text-2xl leading-none">{title}</div>
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}