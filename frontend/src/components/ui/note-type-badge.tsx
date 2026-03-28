import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface NoteTypeBadgeProps {
  type: string
  className?: string
}

function NoteTypeBadge({ type, className }: NoteTypeBadgeProps) {
  const label = type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
  return (
    <Badge noteType={type} className={cn(className)}>
      {label}
    </Badge>
  )
}

export { NoteTypeBadge }
