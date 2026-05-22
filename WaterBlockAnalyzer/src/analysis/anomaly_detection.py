import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import warnings
import warnings

warnings.filterwarnings('ignore')

class WaterNetworkAnomalyDetector:
    """
    DACON 상수도 관망 이상 감지 알고리즘 베이스라인 모델
    
    특징:
    1. 비지도 학습 기반 (Isolation Forest)
    2. 도메인 지식이 결합된 파생 변수(Feature Engineering) 자동 생성
       - 시간대 가중치 (야간최소유량/압력 시간대)
       - 이동 평균 및 편차 (Rolling Statistics)
    3. 오탐 방지를 위한 임계값 조정 및 스케일링 적용
    """
    
    def __init__(self, contamination=0.01, random_state=42):
        """
        초기화
        :param contamination: 전체 데이터 중 이상치(누수/파손)가 차지할 예상 비율 (기본 1%)
        :param random_state: 재현성을 위한 시드
        """
        self.model = IsolationForest(
            n_estimators=100, 
            contamination=contamination, 
            random_state=random_state,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.features = [] # 학습에 사용된 피처 목록
        
    def _create_features(self, df, value_col='pressure'):
        """
        도메인 지식 기반 파생 변수 생성
        :param df: 입력 데이터프레임 (timestamp 인덱스 필수)
        :param value_col: 분석할 대상 컬럼 (예: 수압 'pressure', 유량 'flow')
        :return: 파생 변수가 추가된 데이터프레임
        """
        data = df.copy()
        
        # 1. 시간 파생 변수
        data['hour'] = data.index.hour
        data['dayofweek'] = data.index.dayofweek
        
        # 2. 야간최소유량/수압(MNF) 시간대 가중치 (새벽 2시~4시)
        # 이 시간대의 변동성은 매우 중요하므로 가중치를 줌
        data['is_mnf_time'] = data['hour'].apply(lambda x: 1 if 2 <= x <= 4 else 0)
        
        # 3. 이동 평균 및 이동 표준편차 (단기 및 장기 변동성 포착)
        # 가정: 데이터가 분(Minute) 단위로 들어온다고 가정 (10분, 60분)
        data['rolling_mean_10'] = data[value_col].rolling(window=10, min_periods=1).mean()
        data['rolling_std_10'] = data[value_col].rolling(window=10, min_periods=1).std().fillna(0)
        data['rolling_mean_60'] = data[value_col].rolling(window=60, min_periods=1).mean()
        
        # 4. 수압/유량의 순간 급강하율 (차분값)
        data['diff_1'] = data[value_col].diff().fillna(0)
        
        return data

    def fit(self, df, value_col='pressure'):
        """
        모델 학습 (정상 상태 위주의 데이터로 학습)
        """
        # 피처 엔지니어링
        processed_df = self._create_features(df, value_col)
        
        # 학습에 사용할 피처 선택
        self.features = [value_col, 'rolling_mean_10', 'rolling_std_10', 'diff_1', 'is_mnf_time']
        
        X = processed_df[self.features]
        
        # 데이터 스케일링
        X_scaled = self.scaler.fit_transform(X)
        
        # 모델 학습
        self.model.fit(X_scaled)
        print(f"[학습 완료] 데이터 샘플 수: {len(X_scaled)}, 사용된 피처: {self.features}")
        
    def predict(self, df, value_col='pressure'):
        """
        이상 탐지 예측
        :return: 이상 여부(-1: 이상, 1: 정상) 및 이상 점수가 포함된 데이터프레임
        """
        processed_df = self._create_features(df, value_col)
        X = processed_df[self.features]
        
        X_scaled = self.scaler.transform(X)
        
        # 예측 (1: 정상, -1: 이상)
        processed_df['anomaly'] = self.model.predict(X_scaled)
        
        # 이상 점수 (낮을수록 비정상적)
        processed_df['anomaly_score'] = self.model.decision_function(X_scaled)
        
        # 시각화 및 필터링 편의를 위해 이상 플래그를 0(정상), 1(이상)로 변환
        processed_df['is_anomaly'] = processed_df['anomaly'].apply(lambda x: 1 if x == -1 else 0)
        
        anomaly_count = processed_df['is_anomaly'].sum()
        print(f"[예측 완료] 총 {len(processed_df)}개 샘플 중 이상 감지 건수: {anomaly_count}건")
        
        return processed_df

# ==========================================
# 테스트 코드 (더미 데이터 기반 실행)
# ==========================================
if __name__ == "__main__":
    print("=== DACON 기반 상수도 이상탐지 모듈 테스트 ===")
    
    # 1. 1주일치 분 단위 더미 데이터 생성 (정상 수압: 2.5 ~ 3.5 kgf/cm2)
    dates = pd.date_range(start='2026-05-10', end='2026-05-17', freq='T')
    dummy_pressure = np.random.normal(loc=3.0, scale=0.1, size=len(dates))
    
    df_test = pd.DataFrame({'pressure': dummy_pressure}, index=dates)
    
    # 2. 인위적인 누수/파손 데이터(이상치) 주입 
    # 예: 5월 15일 새벽 2시 30분에 수압 급강하 발생
    leak_time = '2026-05-15 02:30:00'
    leak_idx = df_test.index.get_loc(leak_time)
    df_test.iloc[leak_idx:leak_idx+30, 0] = df_test.iloc[leak_idx:leak_idx+30, 0] - 1.5 # 수압 1.5 급강하
    
    # 3. 모델 초기화 및 학습
    detector = WaterNetworkAnomalyDetector(contamination=0.005)
    detector.fit(df_test, value_col='pressure')
    
    # 4. 예측 수행
    result_df = detector.predict(df_test, value_col='pressure')
    
    # 5. 결과 확인
    anomalies = result_df[result_df['is_anomaly'] == 1]
    print("\n[감지된 이상 내역 (일부)]")
    print(anomalies[['pressure', 'rolling_std_10', 'diff_1', 'anomaly_score']].head(10))
    
    # 6. 시각화 (matplotlib)
    print("\n[시각화 렌더링 중...]")
    plt.style.use('dark_background') # 다크 테마 적용
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 정상 데이터 플롯 (청록색)
    ax.plot(result_df.index, result_df['pressure'], color='#00d2d3', label='Normal Pressure', alpha=0.8, linewidth=1)
    
    # 이상 데이터 포인트 스캐터 플롯 (빨간색)
    ax.scatter(anomalies.index, anomalies['pressure'], color='#ff4757', s=50, zorder=5, label='Anomaly (Leak Detected)')
    
    # 5월 15일 야간 누수 주입 구간 하이라이트
    ax.axvspan(pd.to_datetime('2026-05-15 02:25:00'), pd.to_datetime('2026-05-15 03:00:00'), color='#ff9f43', alpha=0.3, label='Leak Injected Area')
    
    ax.set_title('Water Network Pressure Anomaly Detection (Isolation Forest)', fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Pressure (kgf/cm2)', fontsize=12)
    ax.legend(loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # x축 날짜 포맷
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 이미지 파일로 저장
    save_path = os.path.join(os.path.dirname(__file__), 'anomaly_plot.png')
    plt.savefig(save_path, dpi=300)
    print(f"\n[성공] 이상 탐지 시각화 그래프가 저장되었습니다: {save_path}")
