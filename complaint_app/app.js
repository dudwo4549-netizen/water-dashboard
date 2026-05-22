// S-WATERS 스마트 민원 대응 가이드 - 데이터 엔진 및 앱 제어 로직

// 아바타 SVG/커스텀 이미지 대체용 이모지 및 스타일 클래스
const characters = {
    '서용': { name: '서용 팀장', emoji: '👑', color: '#ff70a6', role: '소통/고객응대' },
    '동룡': { name: '동룡 마스터', emoji: '🛠️', color: '#4cc9f0', role: '기술/관망분석' },
    '옥룡': { name: '옥룡 대장', emoji: '💪', color: '#f77f00', role: '현장안전/시공' }
};

// 민원 가이드 상세 데이터베이스 (환경부 매뉴얼 및 사내 SOP 완벽 반영)
const guideData = {
    'turbidity': {
        category: 'water-quality',
        title: '💧 탁수 및 이물질 민원 대응 가이드',
        desc: '수돗물에서 탁한 물, 적수, 흑수 또는 모래 등 이물질이 나올 때의 현장 표준 SOP',
        steps: [
            {
                stepNum: 1,
                title: '초동 접수 및 관망 데이터 분석',
                char: '동룡',
                speech: '팀장님, 계통 전체의 이상인지 먼저 소블록 내 인근 배수지 탁도계 데이터부터 확인해봅시다!',
                actions: [
                    '민원 주소지 기준 소블록 유입 유량 및 배수지 탁도(Turbidity) 트렌드 실시간 조회',
                    '인근 구역 내 상수도 공사 및 밸브 제어 이력이 24시간 내에 있었는지 확인',
                    '민원인과 연락하여 수돗물 색깔(적수/백수/흑수) 및 발생 시간을 상세하게 파악'
                ]
            },
            {
                stepNum: 2,
                title: '현장 수질 실측 및 원인 판별',
                char: '옥룡',
                speech: '현장으로 출동할 때는 휴대용 탁도계와 잔류염소 측정기를 꼭 챙기고, 계량기 직수부터 뽑아서 재봐야 해요!',
                actions: [
                    '민원가 가옥 계량기 전단 수도꼭지에서 직접 채수 후 탁도 및 잔류염소 수치 측정',
                    '수치 판독: 탁도 0.5 NTU 초과 또는 잔류염소 0.1 mg/L 미만 시 수계 이상으로 확정',
                    '인근 가옥(최소 3가구 이상) 공동 발생 여부 탐문하여 국소적 문제인지 계통적 문제인지 판별'
                ]
            },
            {
                stepNum: 3,
                title: '소화전 퇴수 및 이물질 세척',
                char: '옥룡',
                speech: '이물질은 관로 아래 정체되어 있던 물이 압력 급변으로 튀어나온 겁니다! 인근 소화전을 열어서 대량 퇴수합시다!',
                actions: [
                    '민원 지역 직전 제수밸브 및 배수밸브 확인',
                    '인근 소화전(Fire Hydrant)을 개방하여 맑은 물이 나올 때까지 플러싱(Flushing) 세척 작업 실시',
                    '퇴수 작업 시 배수구 용량과 보행자 안전 펜스 설치 여부 철저히 확인'
                ]
            },
            {
                stepNum: 4,
                title: '주민 공지 및 단수 복구 완료',
                char: '서용',
                speech: '세척 작업 중에는 물을 쓰지 않도록 안내 방송을 정중하게 하고, 맑은 물 공급 시 생수 지원과 완료 안내를 잊지 마세요! 🌻',
                actions: [
                    '탁수 지속 발생 시 임시 음용 제한 통보 및 비상급수용 병물(생수) 긴급 배부',
                    '작업 종료 후 최종 탁도 실측(0.5 NTU 이하 유지 확인)',
                    '민원 대응방에 [퇴수 전/후 사진]과 [측정 수치]를 입력하고 종결 보고'
                ]
            }
        ]
    },
    'larvae': {
        category: 'water-quality',
        title: '🐛 수돗물 유충 발생 의심 대응 가이드',
        desc: '수돗물 내 유충(깔따구 등) 발생 의심 민원 시 현장 역학조사 및 긴급 차단 표준 매뉴얼',
        steps: [
            {
                stepNum: 1,
                title: '초동 여과망 설치 및 샘플 채취',
                char: '옥룡',
                speech: '유충 민원은 주민 불안감이 매우 큽니다. 신속하게 현장으로 가서 샤워기나 계량기 후단에 미세 여과망을 달아 증거를 잡아야 해요!',
                actions: [
                    '민원 수용가 수도꼭지에 미세 멤브레인 여과망(필터)을 즉각 장착하여 유충 생체 포집 시도',
                    '발견된 유충 생체는 멸균 튜브에 담아 보존(연구원 검사 및 깔따구 종 판별 의뢰용)',
                    '민원인에게 유충 발견 당시 물을 받아둔 용기가 있는지 확인하고 수거'
                ]
            },
            {
                stepNum: 2,
                title: '배수지/정수장 모니터링 및 역학 조사',
                char: '동룡',
                speech: '유충이 외부 유입인지 배수지 내부 증식인지 알아야 합니다. 배수지 송수 밸브 여과망부터 바로 스캔해 볼게요.',
                actions: [
                    '해당 소블록에 공급하는 배수지(Reservoir) 상부 해치 개방 및 에어 벤트 여과망 파손 여부 점검',
                    '정수장 활성탄 흡착지(GAC) 여과층 플러싱 물 속 유충 유무 정밀 분석 의뢰',
                    '외부 오염 요인(옥내 물탱크 관리 부실, 배수구 역류 등)과 상수관로 유입 가능성 전방위 비교'
                ]
            },
            {
                stepNum: 3,
                title: '배수지 차단, 긴급 관세척 및 생수 배부',
                char: '서용',
                speech: '배수지 문제로 확진되면 신속히 차단하고 수계 전환을 해야 합니다. 주민들께 생수를 즉시 공급해 드려요!',
                actions: [
                    '정수 유입 밸브 긴급 제어 및 오염된 배수지 드레인(Drain) 배출 조치',
                    '인근 정상 배수지 계통으로부터 수계를 신속히 전환하여 정상 용수 긴급 공급',
                    'K-water 및 인근 지자체 협조를 얻어 대량의 병물(S-WATERS 병물) 수송 및 가옥별 직접 공급 체계 가동'
                ]
            }
        ]
    },
    'pressure-drop': {
        category: 'pressure',
        title: '🚀 수압 저하 및 출수 불량(단수) 가이드',
        desc: '갑자기 물이 안 나오거나 수압이 현저히 약해진 경우의 1-2단계 기술 진단 알고리즘',
        steps: [
            {
                stepNum: 1,
                title: '계량기 전단 압력 실측',
                char: '옥룡',
                speech: '수압 민원은 1단계로 가옥 밖 계량기 앞에서 압력을 재보는 것부터 시작됩니다. 이것으로 원인의 80%가 걸러집니다!',
                actions: [
                    '가옥 수도미터(계량기) 전단 앵글밸브 분리 및 수압계 장착',
                    '정밀 측정 후 압력 판독: \n- **0.7 kgf/㎠ 미만**: 관로 및 시설 오작동\n- **1.5 kgf/㎠ 이상**: 수용가 내부 배관 오작동'
                ]
            },
            {
                stepNum: 2,
                title: '[케이스 A] 수용가 내부 원인 진단 (전단 압력 정상시)',
                char: '동룡',
                speech: '압력이 정상인데 집 안만 물이 안 나오는 건 100% 옥내 문제입니다. 하나씩 체크해 드릴게요.',
                actions: [
                    '**수도 필터 막힘**: 싱크대나 샤워기 내부 거름망에 모래나 녹 찌꺼기 적체 여부 확인 후 즉시 청소',
                    '**옥내 감압밸브(PRV) 오작동**: 옥내 인입단 감압밸브 셋팅 나사를 조절하여 압력 상승 시도',
                    '**옥내 누수 검사**: 집 안의 물을 모두 잠근 후 계량기 별표(지침) 회전 여부 확인 ➔ 누수 감지 시 수용가 자체 수리 안내'
                ]
            },
            {
                stepNum: 3,
                title: '[케이스 B] 관로 및 공급 시설 진단 (전단 압력 불량시)',
                char: '옥룡',
                speech: '계량기 밖 압력이 낮다면 메인 관로에 문제가 생긴 겁니다. 인근 가압장과 메인 제수밸브 상태를 봐야 합니다!',
                actions: [
                    '**블록 밸브 오차단**: 소블록 경계 제수밸브가 엉뚱하게 잠겨 있는지 Vworld 지도 데이터와 대조 점검',
                    '**가압 펌프 오작동**: 고지대 공급용 간이 가압장 펌프 제어반(인버터 주파수) 오동작 확인 및 즉시 리셋',
                    '**메인 관로 누수**: 인근 노면 누수 흔적이나 소블록 야간최소유량(MNF) 급증 데이터 스캔'
                ]
            }
        ]
    },
    'high-pressure': {
        category: 'pressure',
        title: '⚡ 고수압 및 수격 민원 대응 가이드',
        desc: '수압이 너무 강해 보일러가 고장 나거나 배관 진동/소음(수격현상)이 발생하는 민원의 해결법',
        steps: [
            {
                stepNum: 1,
                title: '전단 수압 실측 및 초과 판정',
                char: '동룡',
                speech: '상수도 설계 기준상 수용가 인입 압력은 7.0 kgf/㎠ 이하여야 합니다. 초과 시 계량기 파손 위험이 큽니다.',
                actions: [
                    '계량기 전단에 수압을 측정하여 7.0 kgf/㎠ 이상인지 확인',
                    '주간 압력과 야간 최소사용 시간대(최고 압력 도달 시간)의 압력 편차 비교 분석',
                    '수격 작용(Water Hammering) 발생 징후가 배관 진동이나 쿵쿵거리는 소음으로 관찰되는지 진단'
                ]
            },
            {
                stepNum: 2,
                title: '감압밸브(PRV) 조작 및 신설 조치',
                char: '옥룡',
                speech: '인근 블록 감압밸브 설정압을 낮추거나 개별 수용가 전단에 감압 밸브를 신설하는 것이 가장 확실한 처방이죠!',
                actions: [
                    '해당 구역 공급 메인 관로 상에 설치된 블록 감압밸브(PRV)의 파이럿 밸브 셋팅값 하향 조절',
                    '블록 PRV 조절이 불가능한 고도 차이 지형일 경우, 개별 가옥 계량기 전단에 소형 감압밸브 설치를 사업소에 긴급 제안 및 시공 협의',
                    '조치 후 최종 인입 수압을 2.0 ~ 4.0 kgf/㎠ 수준의 안정적인 범위로 조정 완료'
                ]
            }
        ]
    },
    'leak-road': {
        category: 'leak',
        title: '🚧 도로 노면 및 관로 파손 누수 대응 가이드',
        desc: '도로에서 물이 뿜어져 나오거나 지표면이 젖어 싱크홀 우려가 있는 도로 누수 상황 대응 SOP',
        steps: [
            {
                stepNum: 1,
                title: '현장 긴급 차단 및 통제',
                char: '옥룡',
                speech: '도로 누수는 도로 함몰(싱크홀)이나 교통사고로 이어질 수 있는 극도로 위험한 상황입니다. 안전 조치부터 합시다!',
                actions: [
                    '현장 도착 즉시 도로 누수 분출 지점 주변에 칼라콘 및 안전 테이프, 차량 유도 펜스 긴급 배치',
                    '지반 함몰 및 지하 동공 징후가 노면 균열이나 주저앉음으로 보이는지 확인하고 위험 시 즉시 경찰 협조 요청 및 도로 통제',
                    '수돗물 여부 판별을 위해 현장 염소(Chlorine) 시약 테스트를 실시하여 하수도/용수 유출과 명확히 구분'
                ]
            },
            {
                stepNum: 2,
                title: '단수 범위 파악 및 제수밸브 차단 제어',
                char: '동룡',
                speech: '누수 지점 바로 뒷단의 제수밸브를 신속하게 차단하여 누수 유출량을 차단해야 합니다. 관망 고립 분석을 돌려보겠습니다!',
                actions: [
                    'QGIS WaterBlock Isolator 모바일 뷰어를 통해 누수 구간 고립을 위해 폐쇄해야 할 제수밸브(Sluice Valve) 최소 범위 확인',
                    '밸브 차단으로 인해 단수되는 아파트 및 수용가 가구 수 즉각 집계 ➔ 상황실 긴급 보고 및 단수 문자 발송 요청',
                    '제수밸브 차단 시 급작스러운 차단으로 인한 수격 작용 방지를 위해 회전수를 세어가며 천천히 조작'
                ]
            },
            {
                stepNum: 3,
                title: '굴착 공사 입회 및 관로 복구',
                char: '옥룡',
                speech: '굴착 시에는 타 지하 매설물(가스관, 전기선) 손괴 예방이 핵심입니다. 도면을 잘 맞춰 보며 터파기를 입회하세요!',
                actions: [
                    '복구 업체 굴착기 작업 시 상수관 손상 부위(Ductile Iron Pipe 등) 정밀 크랙 분석',
                    '멀티 조인트 또는 신축관을 사용해 이탈 방지형 누수 복구 자재로 완벽 체결 입회',
                    '통수 후 관내 공기 배출용 공기밸브(Air Valve) 작동 확인 및 관망 데이터 최종 업데이트 마킹'
                ]
            }
        ]
    },
    'leak-meter': {
        category: 'leak',
        title: '🛠️ 수도 계량기 및 보호통 누수 가이드',
        desc: '수용가 계량기 보호통 내부 연결부 파손이나 동파로 인해 물이 고이고 누수되는 소규모 민원 SOP',
        steps: [
            {
                stepNum: 1,
                title: '누수 지점 정밀 적출',
                char: '옥룡',
                speech: '보호통 내부 흙을 걷어내고 앵글밸브와 계량기 신축 연결관 중 어디서 새는지 정확히 찍어야 합니다.',
                actions: [
                    '수도 계량기 보호통(보온재) 내부 침수 물을 펌프로 흡입 배출',
                    '앵글밸브(Angle Valve) 결속 나사부 부식 여부 점검',
                    '수도미터 자체 크랙(동파 흔적) 또는 연결 주름관 핀홀 누수 여부 비눗물 스캔'
                ]
            },
            {
                stepNum: 2,
                title: '부품 신속 교체 및 복구',
                char: '옥룡',
                speech: '보호통 내 결속 부품은 소모품이 많습니다. 규격에 맞는 고무 패킹과 테프론 테이프로 누설을 완벽히 차단합시다.',
                actions: [
                    '계량기 전단 밸브를 잠그고 노후 패킹 즉시 제거 및 고탄성 실리콘 패킹으로 교체 체결',
                    '동파된 수도 계량기는 사업소 자재실로부터 정식 계량기 청구 후 교체 장착 및 봉인 작업 완료',
                    '밸브를 서서히 개방하여 연결부 미세 누설이 전혀 없음을 최종 확인 후 보온재 충진 및 보호통 뚜껑 잠금'
                ]
            }
        ]
    },
    'abuse-verbal': {
        category: 'special',
        title: '🛡️ 고객 폭언 및 욕설 긴급 대처 SOP',
        desc: '현장 또는 통화 중 민원인이 이성을 잃고 폭언, 욕설, 인격비하, 협박을 가할 때의 대응 표준',
        steps: [
            {
                stepNum: 1,
                title: '1차 엄중 경고 및 진정 유도',
                char: '서용',
                speech: '팀장님, 절대 감정적으로 맞대응하지 마세요! 법률에 따른 표준 문구로 차분하고 엄중하게 1차 경고를 하셔야 합니다. 🌻',
                actions: [
                    '단호하고 차분한 어조 유지: "민원인님, 욕설과 인격 비하 발언을 지속하시면 제가 상담을 진행하기 어렵습니다. 진정해 주시기 바랍니다."',
                    '상대방 발언을 자르지 않고 끝까지 듣되, 불법 행위(협박, 성희롱 등) 수위가 올라가는지 냉정히 체크'
                ]
            },
            {
                stepNum: 2,
                title: '녹음 및 웨어러블 캠 가동 고지',
                char: '서용',
                speech: '민원처리법에 따라 폭언 시에는 증거 수집을 위해 녹음이나 촬영이 가능합니다. 이 사실을 반드시 고지하세요!',
                actions: [
                    '표준 고지 멘트 낭독: "민원인님, 지속적인 폭언으로 인해 민원처리법 시행령 제4조에 의거하여 지금부터 이 대화는 녹음(또는 웨어러블 캠 촬영)됨을 알려드립니다."',
                    '보유 중인 모바일 녹음 앱 활성화 또는 현장 안전 조끼의 웨어러블 카메라 녹화 버튼 작동시작'
                ]
            },
            {
                stepNum: 3,
                title: '상담 종료 및 현장 철수',
                char: '서용',
                speech: '고지 후에도 폭언이 멈추지 않으면, 그 즉시 전화를 끊거나 현장에서 분리되어 안전지대로 대피하셔야 합니다.',
                actions: [
                    '종료 멘트: "지속적인 욕설로 인해 상담(또는 점검)을 중단하겠습니다." 고지 후 즉각 통화 종료 또는 현장 이탈 철수',
                    '사업소 내 [특이민원 법적 대응 전담 부서]에 즉시 상황 보고서 제출 및 캡처 녹음본 클라우드 백업 전송'
                ]
            }
        ]
    },
    'disability': {
        category: 'special',
        title: '♿ 교통약자 및 장애인 고객 맞춤 응대 가이드',
        desc: '시각, 청각, 지체, 지적 장애를 가진 민원가 방문 시 실질적으로 동등한 서비스를 제공하기 위한 표준 요령',
        steps: [
            {
                stepNum: 1,
                title: '시각 장애인 고객 응대 요령',
                char: '서용',
                speech: '시각장애인 분들께는 "여기", "저기" 같은 지칭 대명사를 쓰면 안 됩니다! 아주 구체적인 거리와 방향으로 묘사해 드려야 해요.',
                actions: [
                    '공간 구체적 설명: "민원인님, 앞으로 5걸음 이동하신 후 왼쪽으로 90도 회전하시면 접수 창구 의자가 바로 오른편에 있습니다."',
                    '동행 인도 시: 먼저 도움이 필요한지 여쭤보고 동의하시면 내 팔꿈치 뒤쪽을 가볍게 잡게 한 뒤 반걸음 앞서 천천히 안내',
                    '중요 문서 작성 시: 고객의 동의하에 주요 내용을 또박또박 읽어드리고 신청 서식 대필을 진행함'
                ]
            },
            {
                stepNum: 2,
                title: '청각 장애인 고객 응대 요령',
                char: '서용',
                speech: '보청기를 끼셨더라도 큰 소리로 외치기보다는, 마스크를 잠시 내리고 입모양을 또박또박 보여주거나 필담을 쓰는 게 편안합니다.',
                actions: [
                    '필담 도구(테블릿 PC 또는 종이와 펜)를 즉각 준비하여 질문 사항을 텍스트로 명확하게 제시',
                    '소통 시 입모양(구어)을 천천히 정확하게 보여주며 대화하고, 절대 귀 근처에서 소리를 질러 고주파 보청기 충격을 주지 않음',
                    '스마트폰의 실시간 음성-텍스트 변환(STT) 웹 화면을 띄워 고객이 폰 화면으로 대화 내용을 읽도록 조치'
                ]
            },
            {
                stepNum: 3,
                title: '지체/지적 장애인 고객 응대 요령',
                char: '서용',
                speech: '휠체어 고객과 대화할 때는 자세를 가볍게 낮추어 눈높이를 맞춰주는 것만으로도 대단한 존중을 느낍니다! 🌻',
                actions: [
                    '휠체어 이동을 위해 출입구 턱 경사판을 즉각 개방하고, 이동 동선 방해 적치물 신속 제거',
                    '지적 장애인 고객 대면 시: 어린이로 취급하여 반말을 쓰지 않고 본인 연령에 맞는 정중한 높임말과 가장 직관적이고 쉬운 어휘 사용',
                    '답변이 다소 느리거나 명확하지 않더라도 중간에 끊거나 가로채지 않고 인내심을 갖고 끝까지 경청'
                ]
            }
        ]
    }
};

// 배려 표현 번역기 데이터베이스
const translatorDB = [
    { blunt: "기다리세요.", polite: "죄송합니다만, 잠시만 기다려 주시겠습니까?", category: "waiting" },
    { blunt: "모르겠는데요.", polite: "죄송합니다. 그 부분은 제가 정확하게 확인하여 잠시 후에 다시 연락 드려도 괜찮을까요?", category: "unk" },
    { blunt: "할 수 없는데요.", polite: "대단히 죄송합니다. 지금 당장은 처리가 곤란하지만, 해결할 수 있는 대체 방안이 있는지 상황실과 긴급 협의해 보겠습니다.", category: "refuse" },
    { blunt: "예? 뭐라고요?", polite: "죄송합니다. 통화 음질이 다소 고르지 못해 잘 듣지 못했습니다. 번거로우시겠지만 다시 한 번만 정중히 말씀해 주시면 감사하겠습니다.", category: "hear" },
    { blunt: "저희 업무가 아닙니다.", polite: "죄송합니다. 해당 사항은 저희 관할 구역이 아닙니다. 하지만 민원인님이 번거롭지 않으시도록 저희가 담당 관할 부서를 확인하여 직접 연결 조치해 드리겠습니다.", category: "outside" },
    { blunt: "귀찮게 왜 자꾸 전화해요.", polite: "수돗물 불편으로 인해 걱정이 많으셨던 점 충분히 이해합니다. 민원인님의 마음에 깊이 공감하며, 한 시간 내로 복구 현장 상황을 다시 세심하게 브리핑해 드리겠습니다.", category: "repeat" }
];

// 화면 초기화 및 상태 관리
let currentCategory = 'all';

document.addEventListener('DOMContentLoaded', () => {
    renderCategoryCards();
    renderTranslator();
    initTheme();
    setupSearch();
    
    // 시뮬레이터 차트 및 수치 생성 (현장 상황실 시뮬레이션용)
    setInterval(updateSimulatorNumbers, 3000);
});

// 카테고리 필터링 및 리스트 렌더링
function filterCategory(cat) {
    currentCategory = cat;
    
    // 탭 버튼 활성화
    const tabs = document.querySelectorAll('.cat-btn');
    tabs.forEach(tab => {
        if (tab.getAttribute('data-cat') === cat) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    renderCategoryCards();
}

function renderCategoryCards() {
    const grid = document.getElementById('categoryGrid');
    grid.innerHTML = '';
    
    let query = document.getElementById('searchInput').value.toLowerCase().trim();
    
    Object.keys(guideData).forEach(key => {
        const item = guideData[key];
        
        // 카테고리 필터
        if (currentCategory !== 'all' && item.category !== currentCategory) return;
        
        // 검색어 필터
        if (query) {
            const matchTitle = item.title.toLowerCase().includes(query);
            const matchDesc = item.desc.toLowerCase().includes(query);
            const matchSteps = item.steps.some(step => 
                step.title.toLowerCase().includes(query) || 
                step.actions.some(act => act.toLowerCase().includes(query))
            );
            if (!matchTitle && !matchDesc && !matchSteps) return;
        }
        
        const card = document.createElement('div');
        card.className = 'glass-card category-card fade-in';
        card.onclick = () => openGuide(key);
        
        let emoji = '📋';
        if (item.category === 'water-quality') emoji = '💧';
        else if (item.category === 'pressure') emoji = '🚀';
        else if (item.category === 'leak') emoji = '🛠️';
        else if (item.category === 'special') emoji = '🛡️';
        
        card.innerHTML = `
            <div class="card-badge badge-${item.category}">
                ${item.category === 'water-quality' ? '수질' : item.category === 'pressure' ? '수압' : item.category === 'leak' ? '누수' : '특이/장애'}
            </div>
            <div class="card-body">
                <div class="card-icon">${emoji}</div>
                <div class="card-info">
                    <h3>${item.title.replace(/[💧🚀🛠️🛡️🐛⚡🚧♿]/g, '').trim()}</h3>
                    <p>${item.desc}</p>
                </div>
            </div>
            <div class="card-footer-info">
                <span>총 ${item.steps.length}개 조치 단계</span>
                <span class="chevron">→</span>
            </div>
        `;
        grid.appendChild(card);
    });
    
    if (grid.innerHTML === '') {
        grid.innerHTML = `
            <div class="no-result fade-in">
                <div style="font-size:3rem; margin-bottom:15px;">🔍</div>
                <p>일치하는 민원 가이드라인이 없습니다.<br>검색어를 정확하게 입력하셨는지 확인해보세요.</p>
            </div>
        `;
    }
}

// 상세 가이드 열기
function openGuide(id) {
    const data = guideData[id];
    if (!data) return;
    
    const detailView = document.getElementById('detailView');
    const content = document.getElementById('detailContent');
    
    let html = `
        <div class="detail-header fade-in">
            <div class="detail-badge badge-${data.category}">SOP 가이드라인</div>
            <h2>${data.title}</h2>
            <p class="detail-desc">${data.desc}</p>
        </div>
        
        <div class="toggle-mode-container fade-in">
            <button class="mode-toggle-btn active" id="btnManual" onclick="switchDetailMode('manual')">📘 표준 매뉴얼 절차</button>
            <button class="mode-toggle-btn" id="btnWebtoon" onclick="switchDetailMode('webtoon')">💡 서용이 사단 조언</button>
        </div>
        
        <div class="steps-container" id="stepsContainer">
    `;
    
    data.steps.forEach((step, idx) => {
        const char = characters[step.char];
        
        html += `
            <div class="step-wrapper fade-in" style="animation-delay: ${idx * 0.1}s">
                <div class="step-title-row">
                    <span class="step-number">STEP ${step.stepNum}</span>
                    <h3>${step.title}</h3>
                </div>
                
                <!-- 웹툰 조언 말풍선 팁 (토글 기능 지원) -->
                <div class="comic-bubble-wrapper character-advice-mode hidden">
                    <div class="char-avatar" style="background-color: ${char.color}">
                        <span class="char-emoji">${char.emoji}</span>
                    </div>
                    <div class="comic-bubble" style="border-color: ${char.color}">
                        <div class="char-name-label" style="background-color: ${char.color}">${char.name} (${char.role})</div>
                        <p class="bubble-speech">"${step.speech}"</p>
                    </div>
                </div>
                
                <!-- 매뉴얼 액션 리스트 -->
                <div class="manual-card-box">
                    <ul class="action-list">
                        ${step.actions.map(act => {
                            // 줄바꿈 대응 및 굵은 표시 대응
                            const formatted = act.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                            return `
                                <li class="action-item" onclick="toggleCheck(this)">
                                    <span class="checkbox"></span>
                                    <span class="action-text">${formatted}</span>
                                </li>
                            `;
                        }).join('')}
                    </ul>
                </div>
            </div>
        `;
    });
    
    html += `</div>`;
    content.innerHTML = html;
    
    detailView.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // 스크롤 잠금
}

function closeGuide() {
    const detailView = document.getElementById('detailView');
    detailView.classList.add('hidden');
    document.body.style.overflow = 'auto'; // 스크롤 해제
}

// 매뉴얼 vs 웹툰조언 토글
function switchDetailMode(mode) {
    const btnManual = document.getElementById('btnManual');
    const btnWebtoon = document.getElementById('btnWebtoon');
    const advices = document.querySelectorAll('.comic-bubble-wrapper');
    const manualBoxes = document.querySelectorAll('.manual-card-box');
    
    if (mode === 'manual') {
        btnManual.classList.add('active');
        btnWebtoon.classList.remove('active');
        advices.forEach(adv => adv.classList.add('hidden'));
        manualBoxes.forEach(box => box.classList.remove('dimmed-mode'));
    } else {
        btnManual.classList.remove('active');
        btnWebtoon.classList.add('active');
        advices.forEach(adv => adv.classList.remove('hidden'));
        // 조언 모드일 때는 매뉴얼 카드박스 가시성은 유지하되 약간 톤 다운
        manualBoxes.forEach(box => box.classList.add('dimmed-mode'));
    }
}

// 체크박스 클릭 인터랙션
function toggleCheck(element) {
    element.classList.toggle('checked');
}

// 배려 표현 번역기 렌더링 및 기능
function renderTranslator() {
    const list = document.getElementById('translatorList');
    list.innerHTML = '';
    
    translatorDB.forEach((item, idx) => {
        const div = document.createElement('div');
        div.className = 'glass-card translator-card fade-in';
        div.style.animationDelay = `${idx * 0.05}s`;
        div.innerHTML = `
            <div class="trans-left">
                <span class="badge-red">현장 말투</span>
                <p class="blunt-phrase">"${item.blunt}"</p>
            </div>
            <div class="trans-arrow">➔</div>
            <div class="trans-right">
                <span class="badge-green">서용이의 배려 표현 추천</span>
                <p class="polite-phrase" onclick="copyText(this)">"${item.polite}"</p>
                <span class="copy-hint">탭하여 복사</span>
            </div>
        `;
        list.appendChild(div);
    });
}

// 텍스트 클립보드 복사
function copyText(el) {
    const text = el.innerText.replace(/"/g, '');
    navigator.clipboard.writeText(text).then(() => {
        // 복사 알림 토스트 띄우기
        showToast('📋 복사 완료! 대화 및 전송 창에 붙여넣기 하세요.');
    }).catch(err => {
        console.error('복사 실패', err);
    });
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 2500);
}

// 검색 설정
function setupSearch() {
    const input = document.getElementById('searchInput');
    input.addEventListener('input', () => {
        renderCategoryCards();
    });
}

// 다크/라이트 테마 초기화 및 전환
function initTheme() {
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
}

function toggleTheme() {
    const html = document.documentElement;
    let theme = html.getAttribute('data-theme');
    let nextTheme = theme === 'dark' ? 'light' : 'dark';
    
    html.setAttribute('data-theme', nextTheme);
    localStorage.setItem('theme', nextTheme);
    
    // 테마 토글 버튼 아이콘 변경
    const icon = document.querySelector('.theme-btn');
    icon.innerHTML = nextTheme === 'dark' ? '☀️' : '🌙';
    
    showToast(`🎨 ${nextTheme === 'dark' ? '미래형 다크 모드' : '프리미엄 라이트 모드'}로 전환되었습니다.`);
}

// 탭 내비게이션 전환 (홈, 스크립트, 상황실)
function switchTab(tabId, tabElement) {
    const tabs = document.querySelectorAll('.tab-content-page');
    tabs.forEach(t => t.classList.add('hidden-tab'));
    
    document.getElementById(tabId).classList.remove('hidden-tab');
    
    const items = document.querySelectorAll('.tab-item');
    items.forEach(item => item.classList.remove('active'));
    tabElement.classList.add('active');
    
    window.scrollTo(0, 0);
}

// 현장 상황실 시뮬레이터 수치 실시간 난수 변동 (생동감 구현)
function updateSimulatorNumbers() {
    const flowVal = document.getElementById('simFlow');
    const pressVal = document.getElementById('simPress');
    const turbVal = document.getElementById('simTurb');
    
    if (!flowVal || !pressVal || !turbVal) return;
    
    // 원래값: 유량 124.5 m3/h, 수압 2.4 kgf, 탁도 0.04 NTU
    let currentFlow = parseFloat(flowVal.innerText);
    let currentPress = parseFloat(pressVal.innerText);
    let currentTurb = parseFloat(turbVal.innerText);
    
    let newFlow = (currentFlow + (Math.random() - 0.5) * 1.5).toFixed(1);
    let newPress = (currentPress + (Math.random() - 0.5) * 0.1).toFixed(2);
    let newTurb = Math.max(0.01, (currentTurb + (Math.random() - 0.5) * 0.005)).toFixed(3);
    
    flowVal.innerText = newFlow;
    pressVal.innerText = newPress;
    turbVal.innerText = newTurb;
}
