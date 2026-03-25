import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Lazy read — window.API_BASE is injected by Flask at request time after bundling.
// Must be read inside a function, not at module parse time.
export function getAPI(): string {
  return (window as any).API_BASE ?? 'http://127.0.0.1:37491'
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Encode a note path for use in URL path segments.
 *  Encodes each segment individually (spaces, #, ? etc.) but preserves slashes. */
export function encodePath(path: string): string {
  return path.split('/').map(encodeURIComponent).join('/')
}
