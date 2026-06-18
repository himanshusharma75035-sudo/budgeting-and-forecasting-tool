import { cn } from "../lib/utils";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  caption?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, subtitle, caption, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("mb-6 flex flex-wrap items-start justify-between gap-4", className)}>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        {caption && <p className="text-xs text-muted-foreground">{caption}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
