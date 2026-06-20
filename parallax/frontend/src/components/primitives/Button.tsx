import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "../../lib/utils";

type Variant = "primary" | "secondary" | "acid" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md" | "lg";
}

const variantClass: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn",
  acid: "btn-acid",
  ghost: "btn-ghost",
  danger:
    "inline-flex items-center justify-center gap-2 px-5 h-11 text-sm font-medium border border-oxblood bg-oxblood text-bone transition-all duration-300 ease-editorial hover:bg-oxblood-500 hover:shadow-brutal-sm focus:outline-none focus-visible:shadow-brutal disabled:opacity-40",
};

const sizeClass = {
  sm: "h-9 px-3 text-xs",
  md: "h-11 px-5 text-sm",
  lg: "h-14 px-7 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "secondary", size = "md", className, children, ...rest }, ref) => (
    <button
      ref={ref}
      className={cn(variantClass[variant], size === "md" ? "" : sizeClass[size], className)}
      {...rest}
    >
      {children}
    </button>
  )
);
Button.displayName = "Button";
