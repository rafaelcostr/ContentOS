import { cn } from "@/lib/utils";

export function Badge({ className, children, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
