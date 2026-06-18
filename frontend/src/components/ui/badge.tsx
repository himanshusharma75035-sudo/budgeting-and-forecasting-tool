import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "../../lib/utils";

export const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2 h-5 text-xs font-medium [&_svg]:size-3",
  {
    variants: {
      variant: {
        neutral: "bg-muted text-muted-foreground",
        pos: "bg-pos/10 text-pos",
        neg: "bg-neg/10 text-neg",
        warn: "bg-warn/10 text-warn",
        accent: "bg-accent text-accent-foreground",
        outline: "border border-border text-foreground",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
