interface Props {
  label: string;
  value: number | string;
  sub?: string;
  accent?: 'blue' | 'green' | 'amber' | 'gray';
}

const ACCENT: Record<NonNullable<Props['accent']>, string> = {
  blue:  'text-blue-600',
  green: 'text-emerald-600',
  amber: 'text-amber-600',
  gray:  'text-gray-600',
};

export default function MetricWidget({ label, value, sub, accent = 'gray' }: Props): JSX.Element {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${ACCENT[accent]}`}>{value}</p>
      {sub !== undefined && (
        <p className="mt-1 text-xs text-gray-400">{sub}</p>
      )}
    </div>
  );
}
