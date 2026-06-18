import { cn } from "../../lib/utils";

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: DivProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card text-card-foreground shadow-xs",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: DivProps) {
  return <div className={cn("flex flex-col gap-1 p-5 pb-2", className)} {...props} />;
}

export function CardTitle({ className, ...props }: DivProps) {
  return <h3 className={cn("text-sm font-medium leading-none", className)} {...props} />;
}

export function CardDescription({ className, ...props }: DivProps) {
  return <p className={cn("text-sm text-muted-foreground", className)} {...props} />;
}

export function CardContent({ className, ...props }: DivProps) {
  return <div className={cn("p-5 pt-2", className)} {...props} />;
}

export function CardFooter({ className, ...props }: DivProps) {
  return <div className={cn("flex items-center p-5 pt-0", className)} {...props} />;
}
