type Props = {
  change: number;
};

export function PriceBadge({ change }: Props) {
  const isUp = change >= 0;

  return (
    <span
      className={`px-2 py-1 text-xs rounded-full ${
        isUp ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"
      }`}
    >
      {isUp ? "+" : ""}
      {change}%
    </span>
  );
}