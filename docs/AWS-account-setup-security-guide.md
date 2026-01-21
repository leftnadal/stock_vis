# AWS 계정 생성 및 보안 설정 가이드

**목표**: 해킹 방지 + 예상치 못한 비용 폭탄 방지

**작성일**: 2025-12-31
**대상**: AWS 처음 사용하는 개발자

---

## 목차
1. [AWS 계정 생성](#1-aws-계정-생성)
2. [루트 계정 보안 강화 (필수)](#2-루트-계정-보안-강화-필수)
3. [비용 폭탄 방지 설정 (필수)](#3-비용-폭탄-방지-설정-필수)
4. [IAM 사용자 생성 (개발용)](#4-iam-사용자-생성-개발용)
5. [로컬 환경 AWS CLI 설정](#5-로컬-환경-aws-cli-설정)
6. [보안 베스트 프랙티스](#6-보안-베스트-프랙티스)
7. [사고 발생 시 대응 방법](#7-사고-발생-시-대응-방법)

---

## 1. AWS 계정 생성

### 1.1 회원가입

1. **AWS 홈페이지 접속**
   - https://aws.amazon.com/ko/
   - 우측 상단 "AWS 계정 생성" 클릭

2. **이메일 주소 입력**
   - **중요**: 개인 이메일 사용 (회사 이메일은 퇴사 시 접근 불가)
   - 예: `your-email@gmail.com`
   - AWS 계정 이름: `stock-vis-dev` (알아보기 쉬운 이름)

3. **루트 사용자 암호 설정**
   - **최소 요구사항**: 12자 이상, 대소문자 + 숫자 + 특수문자
   - **권장**: 20자 이상 랜덤 암호
   - **도구 사용**: 1Password, Bitwarden 같은 암호 관리자 사용 필수
   - ⚠️ **절대 금지**: 브라우저 저장, 메모장 저장, 쉬운 암호

   ```
   좋은 예: Xk9$mP2#vL8@qR5^nT3!wF7*
   나쁜 예: password123, stockvis2025
   ```

4. **연락처 정보 입력**
   - 개인 또는 전문가 선택: **개인** 선택
   - 이름, 전화번호, 주소 입력 (청구서 발송용)

5. **결제 수단 등록**
   - 신용카드 또는 체크카드 등록
   - **$1 임시 결제** 진행됨 (신원 확인용, 곧 환불)

   ⚠️ **보안 팁**:
   - 한도가 낮은 체크카드 사용 권장 (해킹 시 피해 최소화)
   - 또는 신용카드 + 알림 설정 (결제 시 즉시 SMS)

6. **자격 증명 확인**
   - 전화번호 인증 (자동 전화 또는 SMS)
   - 4자리 코드 입력

7. **지원 플랜 선택**
   - **기본 지원 - 무료** 선택 (개발용으로 충분)

8. **완료**
   - 이메일로 "AWS 계정 생성 완료" 메일 수신
   - 로그인 가능

---

## 2. 루트 계정 보안 강화 (필수)

**루트 계정**: 모든 권한을 가진 계정. 해킹되면 끝입니다.

### 2.1 MFA (Multi-Factor Authentication) 설정 - 최우선

**절대 필수 🔥**: 루트 계정에 MFA를 설정하지 않으면 해킹 위험 100배 증가

1. **AWS 콘솔 로그인**
   - https://console.aws.amazon.com/
   - 루트 사용자 이메일 + 암호 입력

2. **우측 상단 계정 이름 클릭 → "보안 자격 증명"**

3. **"멀티 팩터 인증(MFA)" 섹션 → "MFA 활성화"**

4. **MFA 디바이스 선택**

   **옵션 A: 가상 MFA 앱 (권장)**
   - Google Authenticator (iOS/Android)
   - Authy (iOS/Android/Desktop) - **권장** (백업 기능)
   - 1Password (암호 관리자에 MFA 통합)

   **옵션 B: 하드웨어 MFA (가장 안전)**
   - YubiKey 같은 USB 보안 키 ($50~)

   **옵션 C: SMS MFA (비권장)**
   - SIM 스왑 공격 위험

5. **설정 방법 (Authy 기준)**
   - AWS에서 QR 코드 표시
   - Authy 앱 열기 → "Add Account" → QR 코드 스캔
   - AWS에 Authy가 생성한 6자리 코드 2번 입력
   - ✅ MFA 활성화 완료

6. **백업 코드 저장**
   - MFA 설정 시 표시되는 복구 코드를 **암호 관리자에 저장**
   - 휴대폰 분실 시 이 코드로 복구

### 2.2 루트 계정 Access Key 삭제

루트 계정에는 **절대** Access Key를 만들지 마세요.

1. **보안 자격 증명 → "액세스 키" 섹션**
2. 기존 Access Key가 있다면 **즉시 삭제**
3. 루트 계정은 **웹 콘솔 로그인만** 사용

### 2.3 CloudTrail 활성화 (감사 로그)

모든 API 호출을 기록하여 해킹 흔적 추적 가능

1. **CloudTrail 콘솔 이동**
   - https://console.aws.amazon.com/cloudtrail/

2. **"추적 생성"**
   - 추적 이름: `stock-vis-audit-trail`
   - 스토리지 위치: 새 S3 버킷 생성 (기본값)
   - ✅ **"모든 리전에 대한 추적" 활성화**
   - ✅ **"관리 이벤트" 읽기/쓰기 모두 기록**

3. **비용**: 무료 티어 범위 내 (월 $0~2)

---

## 3. 비용 폭탄 방지 설정 (필수)

**시나리오**: 실수로 EC2 인스턴스를 100개 띄우거나, 해커가 비트코인 채굴 시작
**결과**: 며칠 만에 수백만 원 청구

### 3.1 Billing Alerts 활성화

1. **우측 상단 계정 이름 → "결제 대시보드"**
   - https://console.aws.amazon.com/billing/

2. **좌측 메뉴 → "Billing preferences"**

3. **"결제 알림 수신" 체크박스 활성화**
   - ✅ "PDF 송장을 이메일로 받기"
   - ✅ "무료 사용량 알림 받기"
   - 이메일 주소 확인

### 3.2 CloudWatch Billing Alarm 설정

실시간으로 비용 초과 시 알림

1. **CloudWatch 콘솔 이동**
   - **리전을 "US East (N. Virginia)" - us-east-1로 변경** (중요!)
   - Billing 메트릭은 us-east-1에만 있음

2. **좌측 메뉴 → "경보" → "경보 생성"**

3. **"지표 선택"**
   - "Billing" → "Total Estimated Charge" 선택
   - Currency: USD 선택

4. **경보 임계값 설정**
   ```
   임계값 1: $10 초과 시 알림 (개발 환경)
   임계값 2: $50 초과 시 알림 (경고)
   임계값 3: $100 초과 시 알림 (위험)
   ```

5. **SNS 주제 생성**
   - "새 주제 생성" 선택
   - 주제 이름: `billing-alerts`
   - 이메일 주소 입력
   - ✅ 이메일 확인 링크 클릭 필수

6. **여러 개 만들기**
   - $10, $50, $100 각각 별도 경보 생성
   - **즉시 알림 받을 수 있도록 SMS도 추가 권장**

### 3.3 AWS Budgets 설정 (더 강력한 비용 통제)

1. **Billing 대시보드 → "Budgets"**

2. **"예산 생성"**
   - 예산 유형: **비용 예산** 선택
   - 예산 이름: `stock-vis-monthly-budget`
   - 예산 금액: **$60/월** (프로젝트 예상 비용)

3. **알림 설정**
   ```
   - 80% 도달 시 ($48) → 이메일 알림
   - 100% 도달 시 ($60) → 이메일 + SMS 알림
   - 120% 도달 시 ($72) → 즉시 확인 필요
   ```

4. **Cost Explorer 활성화**
   - 비용 분석 도구 (무료)
   - 어떤 서비스가 돈을 많이 쓰는지 확인 가능

### 3.4 리소스 자동 삭제 정책 (선택)

**Tag 기반 자동 종료** (고급 사용자용)
- 예: `auto-stop: true` 태그가 달린 EC2는 밤 12시에 자동 종료
- Lambda 함수로 구현 가능

---

## 4. IAM 사용자 생성 (개발용)

**원칙**: 루트 계정은 MFA 설정 후 **절대 사용 금지**. IAM 사용자로 작업.

### 4.1 IAM 사용자 생성

1. **IAM 콘솔 이동**
   - https://console.aws.amazon.com/iam/

2. **좌측 메뉴 → "사용자" → "사용자 추가"**

3. **사용자 세부 정보**
   - 사용자 이름: `stock-vis-developer`
   - ✅ **"AWS Management Console 액세스 권한 제공"** 체크
   - 콘솔 암호: 사용자 지정 암호 입력 (강력한 암호)
   - ✅ **"사용자는 다음 로그인 시 새 암호를 생성해야 합니다"** 체크 해제 (본인이니까)

4. **권한 설정**

   **옵션 A: 관리형 정책 직접 연결 (빠른 시작)**
   - "권한 정책 직접 연결" 선택
   - 다음 정책들 선택:
     ```
     - AdministratorAccess (⚠️ 개발 환경에서만)
     ```

   **옵션 B: 최소 권한 원칙 (권장)**
   - "권한 정책 직접 연결" 선택
   - 다음 정책들 선택:
     ```
     - AWSLambda_FullAccess
     - AmazonDynamoDBFullAccess
     - AmazonAPIGatewayAdministrator
     - AmazonS3FullAccess
     - AWSStepFunctionsFullAccess
     - CloudWatchFullAccess
     - AWSCloudFormationFullAccess (CDK 배포용)
     - IAMFullAccess (IAM 역할 생성용)
     ```

   ⚠️ **프로덕션 환경**에서는 옵션 B 필수!

5. **태그 추가 (선택)**
   - Key: `Project`, Value: `stock-vis`
   - Key: `Environment`, Value: `dev`

6. **검토 및 생성**
   - ✅ 사용자 생성 완료
   - 📝 로그인 URL 저장: `https://YOUR-ACCOUNT-ID.signin.aws.amazon.com/console`

### 4.2 IAM 사용자 MFA 설정

IAM 사용자도 MFA 필수!

1. **IAM 콘솔 → "사용자" → `stock-vis-developer` 클릭**

2. **"보안 자격 증명" 탭 → "MFA 디바이스 할당"**

3. **루트 계정과 동일한 방법으로 MFA 설정**
   - Authy 앱에 추가 계정으로 등록
   - 계정 이름: `AWS - stock-vis-developer`

### 4.3 Access Key 생성 (AWS CLI용)

1. **IAM 사용자 → "보안 자격 증명" 탭 → "액세스 키 만들기"**

2. **사용 사례 선택**
   - "Command Line Interface (CLI)" 선택
   - ✅ "위 권장 사항을 이해했으며 액세스 키 생성을 계속하려고 합니다" 체크

3. **설명 태그 추가**
   - 설명: `Local development - MacBook Pro`

4. **액세스 키 생성**
   - 🔑 **Access Key ID**: `AKIAIOSFODNN7EXAMPLE` (예시)
   - 🔐 **Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (예시)

   ⚠️ **중요**:
   - Secret Access Key는 **지금 이 순간만** 볼 수 있음
   - 반드시 **암호 관리자에 저장** (1Password, Bitwarden 등)
   - 절대 GitHub에 커밋하지 말 것!

5. **CSV 다운로드 버튼 클릭**
   - 파일을 안전한 곳에 보관 (암호화된 폴더)
   - 클라우드 동기화 폴더(Dropbox, iCloud)는 피할 것

---

## 5. 로컬 환경 AWS CLI 설정

### 5.1 AWS CLI 설치 확인

```bash
# AWS CLI 버전 확인
aws --version

# 출력 예시: aws-cli/2.13.0 Python/3.11.4 Darwin/23.1.0 exe/x86_64
```

설치 안 되어 있다면:
```bash
# macOS (Homebrew)
brew install awscli

# 또는 공식 설치 프로그램
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

### 5.2 자격 증명 설정

```bash
aws configure
```

대화형 프롬프트에서 입력:
```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: ap-northeast-2
Default output format [None]: json
```

**리전 설명**:
- `ap-northeast-2`: 서울 (한국, 레이턴시 최소)
- `us-east-1`: 버지니아 (가장 많은 서비스 제공, 가장 저렴)

### 5.3 설정 확인

```bash
# 자격 증명 확인
aws sts get-caller-identity
```

출력 예시:
```json
{
  "UserId": "AIDACKCEVSQ6C2EXAMPLE",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/stock-vis-developer"
}
```

✅ 정상적으로 IAM 사용자 정보가 나오면 성공!

### 5.4 자격 증명 파일 위치

```bash
# macOS/Linux
~/.aws/credentials
~/.aws/config

# Windows
C:\Users\USERNAME\.aws\credentials
C:\Users\USERNAME\.aws\config
```

**~/.aws/credentials 파일 내용**:
```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**~/.aws/config 파일 내용**:
```ini
[default]
region = ap-northeast-2
output = json
```

⚠️ **보안**:
- 이 파일들은 절대 GitHub에 커밋하지 말 것!
- `.gitignore`에 추가:
  ```
  .aws/
  *.pem
  *.key
  ```

### 5.5 MFA가 필요한 작업 (선택)

IAM 사용자에 MFA를 설정했다면, 일부 민감한 작업에서 MFA 토큰이 필요합니다.

**임시 자격 증명 생성 (MFA 사용)**:
```bash
aws sts get-session-token \
  --serial-number arn:aws:iam::123456789012:mfa/stock-vis-developer \
  --token-code 123456
```

출력된 임시 자격 증명을 `~/.aws/credentials`에 추가:
```ini
[default-mfa]
aws_access_key_id = ASIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
aws_session_token = FwoGZXIvYXdzEBYaDH...
```

---

## 6. 보안 베스트 프랙티스

### 6.1 절대 하지 말아야 할 것

❌ **루트 계정으로 개발 작업**
- 루트 계정은 MFA 설정 후 금고에 보관

❌ **GitHub에 자격 증명 커밋**
- `.env` 파일, `credentials` 파일 절대 커밋 금지
- GitHub이 자동 탐지하면 AWS가 자격 증명 즉시 무효화

❌ **Access Key를 코드에 하드코딩**
```python
# 나쁜 예 ❌
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
```

❌ **퍼블릭 S3 버킷**
- S3 버킷 기본 설정은 항상 **비공개**
- 꼭 필요한 경우에만 특정 객체만 공개

❌ **보안 그룹 0.0.0.0/0 전체 오픈**
```
나쁜 예: SSH(22) 포트를 0.0.0.0/0에 오픈
좋은 예: SSH(22) 포트를 내 IP에만 오픈
```

### 6.2 해야 하는 것

✅ **환경 변수 사용**
```python
# 좋은 예 ✅
import os
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
```

✅ **AWS Systems Manager Parameter Store 사용**
```python
import boto3
ssm = boto3.client('ssm')
fmp_api_key = ssm.get_parameter(
    Name='/stockvis/dev/fmp-api-key',
    WithDecryption=True
)['Parameter']['Value']
```

✅ **IAM 역할 사용 (Lambda, EC2 등)**
- Lambda 함수에는 Access Key 대신 IAM 역할 부여
- EC2 인스턴스에는 Instance Profile 사용

✅ **Access Key 정기 교체 (90일)**
```bash
# IAM 콘솔에서 Access Key 교체
1. 새 Access Key 생성
2. 애플리케이션에 새 키 적용
3. 구 Access Key 비활성화
4. 일주일 후 구 Access Key 삭제
```

✅ **IAM Access Analyzer 활성화**
- IAM 콘솔 → "Access Analyzer" → "Analyzer 생성"
- 외부에서 접근 가능한 리소스 자동 탐지

✅ **AWS Organizations (여러 계정 관리 시)**
- 개발/스테이징/프로덕션 계정 분리
- 프로덕션 계정에 더 엄격한 정책 적용

### 6.3 정기 보안 점검 (월 1회)

**체크리스트**:
- [ ] IAM 사용자 중 90일 이상 사용하지 않은 계정 삭제
- [ ] 사용하지 않는 Access Key 삭제
- [ ] CloudTrail 로그 확인 (이상한 API 호출 없는지)
- [ ] 비용 리포트 확인 (예상치 못한 비용 증가)
- [ ] S3 버킷 공개 여부 확인
- [ ] 보안 그룹 규칙 검토 (0.0.0.0/0 오픈 항목)

**IAM Credential Report 다운로드**:
```bash
# IAM 콘솔 → "Credential report" → "Download report"
# CSV 파일로 모든 사용자의 자격 증명 상태 확인 가능
```

---

## 7. 사고 발생 시 대응 방법

### 7.1 Access Key 유출 의심 시

**즉시 조치 (5분 내)**:

1. **IAM 콘솔 로그인**
   - https://console.aws.amazon.com/iam/

2. **해당 Access Key 비활성화**
   - "사용자" → 해당 사용자 → "보안 자격 증명"
   - Access Key 옆 "비활성화" 클릭

3. **CloudTrail 로그 확인**
   - 최근 API 호출 기록 확인
   - 의심스러운 활동:
     - 생소한 리전에서의 EC2 인스턴스 생성
     - 대량의 S3 업로드/다운로드
     - IAM 권한 변경

4. **리소스 즉시 삭제**
   - 생성된 적 없는 EC2 인스턴스 → **즉시 종료**
   - 생성된 적 없는 S3 버킷 → **즉시 삭제**

5. **새 Access Key 발급**
   - 비활성화한 키는 24시간 후 삭제

### 7.2 예상치 못한 고액 청구서

**$100 이상 청구 시 대응**:

1. **Cost Explorer 확인**
   - Billing 대시보드 → "Cost Explorer"
   - 어떤 서비스가 비용을 발생시켰는지 확인

2. **흔한 원인**:
   - EC2 인스턴스 종료 안 함 (24시간 가동)
   - RDS 데이터베이스 종료 안 함
   - NAT Gateway 삭제 안 함 (시간당 $0.045)
   - 대용량 S3 데이터 전송
   - Lambda 무한 루프

3. **리소스 정리**
   ```bash
   # 모든 리전의 EC2 인스턴스 확인
   for region in $(aws ec2 describe-regions --query "Regions[].RegionName" --output text); do
     echo "Region: $region"
     aws ec2 describe-instances --region $region --query "Reservations[].Instances[].[InstanceId,State.Name]" --output table
   done
   ```

4. **AWS 지원 센터에 연락**
   - 실수로 인한 청구는 경우에 따라 크레딧 지급 가능
   - 단, 처음 한 번만 (상습 실수는 안 해줌)

### 7.3 계정 잠금/도용 시

1. **즉시 루트 계정 비밀번호 재설정**
   - 로그인 페이지 → "비밀번호를 잊으셨습니까?"
   - 이메일로 재설정 링크 수신

2. **AWS 지원팀 연락**
   - 전화: 1-877-913-3382 (미국)
   - 한국 시간 기준 밤에 전화 필요

3. **신용카드 거래 차단**
   - 카드사에 연락하여 AWS 결제 일시 차단

---

## 8. 프로젝트별 추가 보안 설정

### 8.1 FMP API 키 보안 저장

GitHub에 절대 커밋하지 말고, AWS Parameter Store에 저장:

```bash
aws ssm put-parameter \
  --name "/stockvis/dev/fmp-api-key" \
  --value "YOUR_FMP_API_KEY" \
  --type "SecureString" \
  --description "FMP API Key for Market Movers"
```

Lambda 함수에서 사용:
```python
import boto3

ssm = boto3.client('ssm')
fmp_api_key = ssm.get_parameter(
    Name='/stockvis/dev/fmp-api-key',
    WithDecryption=True
)['Parameter']['Value']
```

### 8.2 CDK 배포 시 환경별 분리

```python
# infrastructure/app.py
dev_env = {
    'account': '123456789012',
    'region': 'ap-northeast-2'
}

# dev 환경은 관대한 정책
# prod 환경은 엄격한 정책
```

---

## 요약: 보안 체크리스트

완료하면 체크하세요:

### 계정 생성
- [ ] AWS 계정 생성 완료
- [ ] 강력한 루트 암호 설정 (20자 이상)
- [ ] 암호 관리자에 저장

### 루트 계정 보안
- [ ] 루트 계정 MFA 활성화 (Authy 권장)
- [ ] 루트 계정 Access Key 삭제 (또는 생성 안 함)
- [ ] CloudTrail 활성화 (모든 리전)

### 비용 폭탄 방지
- [ ] Billing Alerts 활성화
- [ ] CloudWatch Billing Alarm 3개 생성 ($10, $50, $100)
- [ ] AWS Budget 설정 ($60/월)
- [ ] Cost Explorer 활성화

### IAM 사용자
- [ ] IAM 사용자 `stock-vis-developer` 생성
- [ ] IAM 사용자 MFA 활성화
- [ ] Access Key 생성 및 안전 보관
- [ ] 최소 권한 원칙 적용 (프로덕션 시)

### 로컬 환경
- [ ] AWS CLI 설치 확인
- [ ] `aws configure` 완료
- [ ] `aws sts get-caller-identity` 테스트
- [ ] FMP API 키를 Parameter Store에 저장

### 추가 보안
- [ ] `.gitignore`에 `.aws/`, `.env` 추가
- [ ] IAM Access Analyzer 활성화
- [ ] 월 1회 보안 점검 일정 설정

---

## 다음 단계

보안 설정 완료 후:

1. **AWS CDK 설치**
   ```bash
   npm install -g aws-cdk
   cdk --version
   ```

2. **CDK 프로젝트 초기화** (다음 문서로)
   - `docs/phase0-cdk-setup.md` 참조

3. **첫 배포 테스트**
   - 간단한 Lambda 함수 배포로 CDK 작동 확인

---

## 참고 자료

- [AWS 보안 모범 사례](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Well-Architected Framework - 보안 기둥](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [AWS 비용 최적화](https://aws.amazon.com/ko/pricing/cost-optimization/)
- [FMP API 문서](https://site.financialmodelingprep.com/developer/docs)

---

**작성일**: 2025-12-31
**작성자**: Claude (Stock-Vis 프로젝트)
**버전**: 1.0
