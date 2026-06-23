import {
  Calculator,
  GitCompareArrows,
  LayoutDashboard,
  LineChart,
  type LucideIcon,
  PiggyBank,
  Table2,
  Upload,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  group: string;
}

export const navItems: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, group: "Overview" },
  { to: "/budgets", label: "Budgets", icon: PiggyBank, group: "Plan" },
  { to: "/drivers", label: "Drivers", icon: Calculator, group: "Plan" },
  { to: "/forecasts", label: "Forecasts", icon: LineChart, group: "Plan" },
  { to: "/variance", label: "Variance", icon: GitCompareArrows, group: "Analyze" },
  { to: "/accounts", label: "Accounts", icon: Table2, group: "Data" },
  { to: "/import", label: "Data Import", icon: Upload, group: "Data" },
];

export const navGroups: string[] = ["Overview", "Plan", "Analyze", "Data"];
