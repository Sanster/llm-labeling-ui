import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function replaceAll(
  str: string,
  search: string,
  replacement: string,
  matchCase = true,
) {
  if (matchCase) {
    return str.replaceAll(search, replacement);
  } else {
    let re = new RegExp(search, 'gi');
    return str.replace(re, replacement);
  }
}
