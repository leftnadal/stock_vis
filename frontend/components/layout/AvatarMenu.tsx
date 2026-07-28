'use client'

// 우측 아바타 메뉴 (P-B): Profile 진입점(/mypage 페이지는 유지) + 로그아웃.
// 다중 사용자 이음새 겸용(향후 계정 전환).
import { useEffect, useRef, useState } from 'react'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { LogOut, User as UserIcon } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'

export function AvatarMenu() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  if (!user) {
    return (
      <Link
        href="/login"
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        로그인
      </Link>
    )
  }

  const displayName = user.nick_name || user.user_name

  const handleLogout = async () => {
    await logout()
    setOpen(false)
    router.push('/')
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200"
        aria-label="계정 메뉴"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <UserIcon className="h-5 w-5" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-2 w-48 rounded-xl border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
        >
          <div className="border-b border-gray-100 px-3 py-2 text-sm text-gray-500 dark:border-gray-800">
            {displayName}님
          </div>
          <Link
            href="/mypage"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
            role="menuitem"
          >
            <UserIcon className="h-4 w-4" /> 프로필
          </Link>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-gray-50 dark:hover:bg-gray-800"
            role="menuitem"
          >
            <LogOut className="h-4 w-4" /> 로그아웃
          </button>
        </div>
      )}
    </div>
  )
}
