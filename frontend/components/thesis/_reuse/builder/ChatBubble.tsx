'use client'

interface Props {
  role: 'ai' | 'user'
  children?: React.ReactNode
  isLoading?: boolean
}

export function ChatBubble({ role, children, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex justify-start mb-3">
        <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]
                        flex items-center gap-1.5 min-h-[44px]">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:200ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce [animation-delay:400ms]" />
        </div>
      </div>
    )
  }

  const isAi = role === 'ai'

  return (
    <div className={`flex ${isAi ? 'justify-start' : 'justify-end'} mb-3`}>
      <div className={`rounded-2xl px-4 py-3 max-w-[85%] text-sm leading-relaxed
                       whitespace-pre-line
                       ${isAi
                         ? 'bg-gray-800 text-gray-200 rounded-tl-sm'
                         : 'bg-blue-600 text-white rounded-tr-sm'}`}>
        {children}
      </div>
    </div>
  )
}
