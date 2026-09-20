"use client";

import { X } from "lucide-react";
import { useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";

export function MobileNav({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex md:hidden">
      <button
        aria-label="Close navigation"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="glass-raised animate-fade-in-up relative z-10 flex h-full w-72 flex-col">
        <button
          onClick={onClose}
          aria-label="Close navigation"
          className="absolute right-3 top-4 rounded-md p-1.5 text-muted hover:bg-surface-hover hover:text-foreground"
        >
          <X size={18} />
        </button>
        <Sidebar onNavigate={onClose} />
      </div>
    </div>
  );
}
