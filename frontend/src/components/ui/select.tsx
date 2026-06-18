import { ChevronDown } from "lucide-react";
import { forwardRef } from "react";

import { cn } from "../../lib/utils";

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

/** Lightweight styled native <select> — accessible and dependency-free. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <div className="relative inline-flex w-full">
      <select
        ref={ref}
        className={cn(
          "h-9 w-full appearance-none rounded-md border border-input bg-card pl-3 pr-9 text-sm text-foreground shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  ),
);
Select.displayName = "Select";
