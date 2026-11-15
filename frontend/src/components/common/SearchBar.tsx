interface Props { value: string; onChange: (value: string) => void; placeholder?: string; label?: string }

export default function SearchBar({ value, onChange, placeholder = 'Search', label = 'Search' }: Props) {
  return (
    <input type="search" aria-label={label} placeholder={placeholder} value={value}
      onChange={(e) => onChange(e.target.value)} className="rounded-md border px-3 py-1.5 text-sm" />
  )
}
