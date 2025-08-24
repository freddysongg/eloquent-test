'use client';

import { Toaster as SonnerToaster } from 'sonner';
import { useTheme } from 'next-themes';

export function Toaster() {
  const { theme = 'system' } = useTheme();

  return (
    <SonnerToaster
      className="toaster group"
      theme={theme as 'light' | 'dark' | 'system'}
      position="bottom-right"
      expand={true}
      richColors
      closeButton
      toastOptions={{
        className: 'group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg',
        classNames: {
          description: 'group-[.toast]:text-muted-foreground',
          actionButton: 'group-[.toast]:bg-primary group-[.toast]:text-primary-foreground',
          cancelButton: 'group-[.toast]:bg-muted group-[.toast]:text-muted-foreground',
        }
      }}
    />
  );
}