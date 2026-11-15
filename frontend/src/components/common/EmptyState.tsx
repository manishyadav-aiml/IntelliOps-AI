export default function EmptyState({ message }: { message: string }) {
  return <p className="rounded-md border border-dashed p-6 text-center text-sm text-slate-500">{message}</p>
}
