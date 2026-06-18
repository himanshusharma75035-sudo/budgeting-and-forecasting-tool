import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

export interface ChartCardProps {
  title: string;
  /** top-right slot for legend / toggles */
  aside?: React.ReactNode;
  height?: number;
  className?: string;
  children: React.ReactNode;
}

export function ChartCard({ title, aside, height = 320, className, children }: ChartCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex-row items-center justify-between pb-3">
        <CardTitle>{title}</CardTitle>
        {aside && <div className="flex items-center gap-2 text-xs text-muted-foreground">{aside}</div>}
      </CardHeader>
      <CardContent className="pt-0">
        <div style={{ height }}>{children}</div>
      </CardContent>
    </Card>
  );
}
