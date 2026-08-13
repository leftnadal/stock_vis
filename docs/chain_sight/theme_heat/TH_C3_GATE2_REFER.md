# TH-C3-LLM-DICT-1 게이트② — 검증자 회부 30건 (결정36=3+ ⑵ 수동 판정)

> K4-명문 3차 판정이 recheck와 불일치한 실질이견. term별 근거 첨부. 사용자(검증자)가 처분 확정.

> 형식: term | recheck should_be(=현 disposition) | 2차LLM | 3차LLM(K4명문) | recheck 근거


## A_recheck과배정(3차=none) (14건)

- **Keel Infrastructure AI** | recheck=`Industrials` | 2차=['Technology'] | 3차=none
  - 근거: Keel Infrastructure는 산업재 섹터 기업이므로, AI 관련 뉴스라도 해당 기업의 섹터를 따르는 것이 원칙임.
- **interest rate hike pressure** | recheck=`Financial Services` | 2차=[] | 3차=none
  - 근거: 금리 인상은 금융 시장의 직접적인 주제이므로 금융 서비스 섹터가 적절함. 거시경제는 'none'으로 분류됨.
- **AI bubble burst** | recheck=`Financial Services` | 2차=['Technology'] | 3차=none
  - 근거: AI 버블은 AI 관련 기업들의 시장 가치 평가 및 시장 구조에 대한 논의이므로 Financial Services 섹터가 적절하다.
- **AI bubble pop** | recheck=`Financial Services` | 2차=[] | 3차=none
  - 근거: AI 버블 붕괴는 AI 관련 기업들의 시장 가치 평가 및 시장 구조에 대한 논의이므로 Financial Services 섹터가 적절하다.
- **AI cost disclosure** | recheck=`Financial Services` | 2차=['Technology'] | 3차=none
  - 근거: AI 비용 공개는 기업의 재무 보고 및 시장 투명성과 관련된 이슈이므로 Financial Services 섹터가 적절하다.
- **AI economy froth** | recheck=`Financial Services` | 2차=['Financial Services', 'Technology'] | 3차=none
  - 근거: 'AI economy froth'는 AI 관련 시장의 과열 및 투기적 현상에 대한 논의이므로 Financial Services 섹터가 적절하다.
- **AI financial security** | recheck=`Financial Services` | 2차=['Financial Services', 'Technology'] | 3차=none
  - 근거: AI가 금융 보안에 활용되는 맥락이므로 금융 서비스 섹터가 적절하다. (K2)
- **AI power demand** | recheck=`Utilities, Technology` | 2차=['Utilities'] | 3차=none
  - 근거: AI로 인한 전력 수요는 Utilities 섹터와 직접적인 관련이 있으며, AI는 Technology 섹터입니다.
- **AI regulation bill** | recheck=`Technology` | 2차=[] | 3차=none
  - 근거: AI 규제 법안은 AI 기술 자체에 대한 것이므로 Technology 섹터가 적절합니다. 'Regulation'은 GICS 섹터가 아닙니다.
- **Bank of Canada recession** | recheck=`Financial Services` | 2차=[] | 3차=none
  - 근거: 캐나다 중앙은행 관련 뉴스로 Financial Services 섹터에 해당하며, 'Macro'는 섹터가 아닙니다.
- **Illinois AI regulation** | recheck=`Technology` | 2차=[] | 3차=none
  - 근거: 'Regulation'은 섹터가 아니며, AI 규제는 기술 섹터에 대한 주제이므로 기술 섹터로 분류해야 합니다.
- **antitrust probe Google** | recheck=`Technology` | 2차=['Communication Services'] | 3차=none
  - 근거: Google에 대한 독점 금지 조사는 Google의 GICS Technology 섹터에 해당합니다. 'Regulation'은 섹터가 아닙니다.
- **central bank gold buying** | recheck=`Financial Services` | 2차=['Basic Materials', 'Financial Services'] | 3차=none
  - 근거: 'gold' 토큰이 중앙은행의 금융 활동 맥락에서 Basic Materials로 오배정되는 구조적 오류가 있습니다.
- **high bond yields AI** | recheck=`Financial Services` | 2차=[] | 3차=none
  - 근거: 'bond yields'는 금융 상품 또는 거시 경제 주제이므로 금융 서비스 또는 none으로 분류해야 하며, 다중 섹터 할당은 허용되지 않습니다.

## B_K3_IPO이견 (5건)

- **SpaceX IPO** | recheck=`Industrials` | 2차=['Financial Services'] | 3차=['Financial Services']
  - 근거: SpaceX는 항공우주 산업 기업이므로 IPO 관련 뉴스라도 해당 기업의 섹터인 Industrials로 분류되어야 한다.
- **SpaceX IPO anticipation** | recheck=`Industrials` | 2차=['Financial Services'] | 3차=['Financial Services']
  - 근거: SpaceX는 항공우주 산업 기업이므로 IPO 관련 뉴스라도 해당 기업의 섹터인 Industrials로 분류되어야 한다.
- **SpaceX IPO buzz** | recheck=`Industrials` | 2차=['Financial Services'] | 3차=['Financial Services']
  - 근거: SpaceX는 항공우주 산업 기업이므로 IPO 관련 뉴스라도 해당 기업의 섹터인 Industrials로 분류되어야 한다.
- **SpaceX IPO surge** | recheck=`Industrials` | 2차=['Financial Services'] | 3차=['Financial Services']
  - 근거: SpaceX는 항공우주 산업 기업이므로 IPO 관련 뉴스라도 해당 기업의 섹터인 Industrials로 분류되어야 한다.
- **health tech IPO** | recheck=`Financial Services` | 2차=['Healthcare'] | 3차=['Healthcare']
  - 근거: IPO는 금융 시장 구조에 관한 주제이므로 K3 규칙에 따라 금융 서비스 섹터로 분류해야 합니다.

## C_기업GICS/기타이견 (11건)

- **Alphabet infrastructure bet** | recheck=`Technology` | 2차=['Communication Services', 'Technology'] | 3차=['Communication Services', 'Technology']
  - 근거: Alphabet의 인프라 투자는 주로 IT 인프라를 의미하며 이는 Technology 섹터에 해당합니다.
- **FuelCell Energy data center** | recheck=`Energy` | 2차=['Industrials'] | 3차=['Industrials']
  - 근거: FuelCell Energy는 Energy 섹터 기업이며, 데이터 센터 관련 활동도 본업의 연장선으로 볼 수 있음 (K2 규칙 적용).
- **oil shipping lane** | recheck=`Industrials` | 2차=['Energy', 'Industrials'] | 3차=['Energy', 'Industrials']
  - 근거: 석유 운송 경로는 운송 인프라에 해당하므로 Industrials 섹터로 분류하는 것이 더 적절하다.
- **AI payment infrastructure** | recheck=`Financial Services, Technology` | 2차=['Financial Services'] | 3차=['Financial Services']
  - 근거: 결제 인프라는 금융 서비스의 핵심이며, AI는 이를 지원하는 기술이므로 Financial Services 섹터가 포함되어야 합니다.
- **AI personal finance** | recheck=`Financial Services, Technology` | 2차=['Financial Services'] | 3차=['Financial Services']
  - 근거: 개인 금융은 Financial Services 섹터에 해당하며, AI는 이를 활용하는 기술입니다.
- **Amazon bond sale** | recheck=`Financial Services` | 2차=['Consumer Cyclical'] | 3차=['Consumer Cyclical']
  - 근거: 기업의 채권 발행은 금융 상품 관련 활동으로 Financial Services 섹터에 해당하며, Macro는 적절하지 않습니다.
- **FCEL EXIM Bank** | recheck=`Energy` | 2차=['Industrials'] | 3차=['Industrials']
  - 근거: FCEL은 Energy 섹터 기업이며, 은행은 거래 주체일 뿐이므로 FCEL의 섹터를 따라야 함 ('bank' 토큰의 구조적 오매칭).
- **Talen Energy AI** | recheck=`Energy` | 2차=['Utilities'] | 3차=['Utilities']
  - 근거: Talen Energy는 Energy 섹터 기업이므로 AI 기술 적용 뉴스라도 해당 기업의 주 섹터인 Energy로 분류되어야 한다.
- **Twilio AI impact** | recheck=`Communication Services` | 2차=['Technology'] | 3차=['Technology']
  - 근거: Twilio는 Communication Services 섹터 기업이므로 AI 기술 영향 뉴스라도 해당 기업의 주 섹터인 Communication Services로 분류되어야 한다.
- **nuclear energy resistance** | recheck=`Utilities` | 2차=['Energy'] | 3차=['Energy']
  - 근거: 'nuclear energy'는 주로 전력 생산과 관련되므로 유틸리티 섹터가 더 적합합니다.
- **telco banking AI** | recheck=`Financial Services` | 2차=['Communication Services', 'Financial Services'] | 3차=['Communication Services', 'Financial Services']
  - 근거: 통신사(Communication Services)가 AI(Technology)를 활용한 뱅킹(Financial Services)을 다루는 복합적인 주제로, 단일 섹터로 분류하기 어려우며 Communication Se