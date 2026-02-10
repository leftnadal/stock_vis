'use client'

import { useState, useEffect } from 'react'
import { X, Share2, Copy, Check } from 'lucide-react'

interface SharePresetModalProps {
  isOpen: boolean
  onClose: () => void
  preset: { id: number; name: string; share_code?: string }
  onShare: (presetId: number) => Promise<{ share_code: string; share_url: string }>
}

export default function SharePresetModal({
  isOpen,
  onClose,
  preset,
  onShare,
}: SharePresetModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shareData, setShareData] = useState<{ share_code: string; share_url: string } | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (isOpen && preset.share_code) {
      // 이미 공유 코드가 있으면 URL 생성
      const baseUrl = window.location.origin
      setShareData({
        share_code: preset.share_code,
        share_url: `${baseUrl}/screener?import=${preset.share_code}`,
      })
    } else {
      setShareData(null)
    }
    setError(null)
    setCopied(false)
  }, [isOpen, preset])

  const handleShare = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await onShare(preset.id)
      setShareData(data)
    } catch (err: any) {
      console.error('프리셋 공유 실패:', err)

      if (err.response) {
        const status = err.response.status
        const data = err.response.data

        if (status === 400) {
          setError(data.detail || '잘못된 요청입니다.')
        } else if (status === 401) {
          setError('인증이 필요합니다. 다시 로그인해주세요.')
        } else if (status === 403) {
          setError('권한이 없습니다.')
        } else if (status === 404) {
          setError('프리셋을 찾을 수 없습니다.')
        } else {
          setError('공유 중 오류가 발생했습니다.')
        }
      } else {
        setError('서버와 연결할 수 없습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!shareData) return

    try {
      await navigator.clipboard.writeText(shareData.share_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('클립보드 복사 실패:', err)
      setError('클립보드 복사에 실패했습니다.')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-md w-full">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-[#30363D]">
          <div className="flex items-center space-x-2">
            <Share2 className="h-5 w-5 text-[#7D8590]" />
            <h2 className="text-xl font-semibold text-white">프리셋 공유</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[#7D8590] hover:text-white transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <div className="mb-4">
            <p className="text-sm text-[#7D8590] mb-1">프리셋 이름</p>
            <p className="text-white font-medium">{preset.name}</p>
          </div>

          {/* Share URL or Share Button */}
          {shareData ? (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-[#7D8590] mb-2">공유 URL</p>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={shareData.share_url}
                    className="flex-1 px-3 py-2 bg-[#0D1117] border border-[#30363D] rounded-lg text-white text-sm focus:outline-none focus:border-[#58A6FF]"
                  />
                  <button
                    onClick={handleCopy}
                    className="px-4 py-2 bg-[#238636] hover:bg-[#2EA043] text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4" />
                        <span>복사됨</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        <span>복사</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="bg-[#0D1117] border border-[#30363D] rounded-lg p-3">
                <p className="text-xs text-[#7D8590]">
                  이 URL을 공유하면 다른 사용자가 프리셋을 가져올 수 있습니다.
                  공유 링크는 90일간 유효합니다.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-[#0D1117] border border-[#30363D] rounded-lg p-4">
                <p className="text-sm text-[#7D8590]">
                  프리셋을 공유하면 다른 사용자가 동일한 필터 조건을 사용할 수 있습니다.
                  공유 링크는 90일간 유효합니다.
                </p>
              </div>

              <button
                onClick={handleShare}
                disabled={loading}
                className="w-full px-6 py-3 bg-[#238636] hover:bg-[#2EA043] text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>공유 링크 생성 중...</span>
                  </>
                ) : (
                  <>
                    <Share2 className="h-5 w-5" />
                    <span>공유 링크 생성</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-4 bg-[#DA3633] bg-opacity-10 border border-[#DA3633] rounded-lg p-3">
              <p className="text-sm text-[#FF7B72]">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#30363D] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[#7D8590] hover:text-white font-medium transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}
