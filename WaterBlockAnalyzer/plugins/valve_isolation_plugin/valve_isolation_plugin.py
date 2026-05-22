import os
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject
from qgis.gui import QgsMapToolIdentifyFeature

from .core_logic import run_isolation

class ValveIsolationPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.map_tool = None

    def initGui(self):
        # 툴바와 메뉴에 액션 추가
        self.action = QAction("🚨 고립확인 (차단밸브 자동선택)", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.action.setCheckable(True)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&S-WATERS", self.action)

    def unload(self):
        # 플러그인 해제 시 정리
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&S-WATERS", self.action)
        if self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)

    def run(self):
        if self.action.isChecked():
            # 관로 레이어 찾기
            layers = QgsProject.instance().mapLayersByName('WTL_PIPE_LM')
            if not layers:
                QMessageBox.warning(self.iface.mainWindow(), "레이어 오류", "WTL_PIPE_LM 레이어를 찾을 수 없습니다.")
                self.action.setChecked(False)
                return
            
            # 맵 툴 활성화 (피처 식별)
            self.map_tool = QgsMapToolIdentifyFeature(self.iface.mapCanvas())
            self.map_tool.setLayer(layers[0])
            self.map_tool.featureIdentified.connect(self.on_feature_identified)
            self.iface.mapCanvas().setMapTool(self.map_tool)
            self.iface.messageBar().pushMessage("안내", "지도에서 단수 구역을 확인할 관로를 클릭하세요.", level=0, duration=5)
        else:
            # 맵 툴 비활성화
            if self.map_tool:
                self.iface.mapCanvas().unsetMapTool(self.map_tool)

    def on_feature_identified(self, feature):
        # 클릭한 피처의 IDN 가져오기
        ftr_idn = feature.attribute('FTR_IDN')
        if not ftr_idn:
            QMessageBox.warning(self.iface.mainWindow(), "속성 오류", "클릭한 관로에 FTR_IDN 값이 없습니다.")
            return

        # 맵 툴 해제 (한 번 클릭 후 원래 도구로 복귀)
        self.action.setChecked(False)
        self.iface.mapCanvas().unsetMapTool(self.map_tool)
        
        # 격리 분석 실행
        try:
            run_isolation(self.iface, str(ftr_idn).strip())
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "분석 오류", f"분석 중 오류가 발생했습니다:\n{str(e)}")
