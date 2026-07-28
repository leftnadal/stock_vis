/** @type {import('next').NextConfig} */

// fail-fast (#55, FE-DEAD-8000-SWEEP): 앱 API base는 절대 URL(NEXT_PUBLIC_API_URL) 단일 규약.
// env 미설정 시 빌드/기동을 즉시 중단해 누락을 드러낸다(죽은 포트 폴백/stale rewrite 제거).
if (!process.env.NEXT_PUBLIC_API_URL) {
  throw new Error(
    'NEXT_PUBLIC_API_URL 미설정 — 빌드/기동 중단(#55, FE-DEAD-8000-SWEEP). ' +
      '.env(.local)에 절대 base(예: http://localhost:18765/api/v1)를 설정하세요.'
  );
}

const nextConfig = {
  reactStrictMode: true,

  // 구 API 프록시 rewrite(죽은 포트 대상)는 제거됨 — 모든 앱 호출은 절대 base(NEXT_PUBLIC_API_URL) 직결
  // (telemetry FIX-1과 동일 규약: 상대 '/api/v1' 경로 미사용, 잔존 상대 호출 0).

  // CORS 설정
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,DELETE,PATCH,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
        ],
      },
    ];
  },

  // 환경 변수: NEXT_PUBLIC_* 는 Next가 자동 인라인 — 별도 env 블록/기본값 불필요.
  // (구 죽은 포트 기본값 제거 — 위 fail-fast 게이트가 NEXT_PUBLIC_API_URL 존재를 강제.)

  // 이미지 도메인 설정
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '**',
        pathname: '/**',
      },
    ],
  },

  // 개발 서버 설정
  devIndicators: {
    buildActivity: true,
    buildActivityPosition: 'bottom-right',
  },

  // TypeScript 설정
  typescript: {
    // 프로덕션 빌드 시 타입 에러 무시 (개발 중에만)
    ignoreBuildErrors: false,
  },
};

module.exports = nextConfig;