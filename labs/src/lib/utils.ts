import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Utility function to generate unique IDs
export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};
