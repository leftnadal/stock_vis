import { Toaster } from 'sonner'

export default function ThesisLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950 animate-fadeIn">
      {children}
      <Toaster position="bottom-center" theme="dark" />
    </div>
  )
}
