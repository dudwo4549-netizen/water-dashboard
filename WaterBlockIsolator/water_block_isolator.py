from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject, QgsMapLayerProxyModel

# Initialize Qt resources from file resources.py (which we will mock or ignore if not using icons)
# import resources

from .water_block_isolator_dialog import WaterBlockIsolatorDialog
import os.path

class WaterBlockIsolatorPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = u'&WaterBlock Isolator'

        self.first_start = None
        self.dlg = None
        # Phase 5: 분석 결과 저장용 인스턴스 변수
        self._found_valves = set()
        self._last_block_name = ""
        self._valve_layer = None

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ''
        self.add_action(
            icon_path,
            text=u'WaterBlock Isolator',
            callback=self.run,
            parent=self.iface.mainWindow())

        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(u'&WaterBlock Isolator', action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        if self.first_start == True:
            self.first_start = False
            self.dlg = WaterBlockIsolatorDialog()
            
            # Layer Filters: Only allow specific geometry types
            self.dlg.mcbPipeLayer.setFilters(QgsMapLayerProxyModel.LineLayer)
            self.dlg.mcbValveLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
            self.dlg.mcbBlockLayer.setFilters(QgsMapLayerProxyModel.PolygonLayer)
            
            # Connect buttons
            self.dlg.btnAnalyze.clicked.connect(self.on_analyze_clicked)
            self.dlg.btnExport.clicked.connect(self.on_export_clicked)

        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    def on_analyze_clicked(self):
        """Handle analyze button click event"""
        pipe_layer = self.dlg.mcbPipeLayer.currentLayer()
        valve_layer = self.dlg.mcbValveLayer.currentLayer()
        block_layer = self.dlg.mcbBlockLayer.currentLayer()

        if not pipe_layer or not valve_layer or not block_layer:
            QMessageBox.warning(self.dlg, "경고", "관로, 밸브, 블록 레이어를 모두 선택해야 합니다.")
            return

        selected_blocks = block_layer.selectedFeatures()
        if not selected_blocks:
            QMessageBox.warning(self.dlg, "경고", "블록 레이어에서 분석할 소블록을 선택(Select)해주세요.")
            return

        block_feat = selected_blocks[0]
        
        # 블록명 필드 자동 인식 (휴리스틱)
        block_name = "이름없음"
        for field in block_feat.fields():
            fname = field.name().upper()
            if "블록" in fname or "명" in fname or "BLK" in fname or "NM" in fname or "NAME" in fname:
                block_name = str(block_feat[field.name()])
                if block_name and block_name.strip() != 'NULL':
                    break
        if block_name == "이름없음" and block_feat.attributes():
            block_name = str(block_feat.attribute(0))

        self.dlg.txtResult.setHtml(f"<b>선택된 블록: <span style='color:blue;'>{block_name}</span></b><br>")
        self.dlg.txtResult.append("분석을 시작합니다...<br>")
        QCoreApplication.processEvents()

        try:
            # ==========================================
            # Phase 2: 블록 경계선과 교차하는 관로 탐색
            # ==========================================
            from qgis.core import QgsFeatureRequest, QgsSpatialIndex, QgsRectangle
            
            block_geom = block_feat.geometry()
            if not block_geom or block_geom.isEmpty():
                self.dlg.txtResult.append("<span style='color:red;'>오류: 선택된 블록의 공간 데이터가 없습니다.</span>")
                return
                
            # 관로 레이어에서 교차하는 객체 찾기 (빠른 처리를 위해 BBox 필터링 적용)
            request = QgsFeatureRequest().setFilterRect(block_geom.boundingBox())
            crossing_pipes = []
            for pipe in pipe_layer.getFeatures(request):
                pipe_geom = pipe.geometry()
                if pipe_geom and not pipe_geom.isEmpty():
                    # 관로가 블록과 교차(intersects)하지만, 완전히 내부(within)에 있지는 않은 경우 -> 경계를 통과하는 유출입 관로
                    if pipe_geom.intersects(block_geom) and not pipe_geom.within(block_geom):
                        crossing_pipes.append(pipe)

            self.dlg.txtResult.append(f"▶ 블록 경계를 통과하는 유출입 관로: <b>{len(crossing_pipes)}</b>개 발견")
            QCoreApplication.processEvents()

            if not crossing_pipes:
                self.dlg.txtResult.append("<br><span style='color:red;'>경계를 통과하는 관로가 없습니다. 단수 밸브 탐색을 종료합니다.</span>")
                return

            # ==========================================
            # Phase 3: 네트워크 추적을 통한 제수밸브 탐색 (BFS)
            # ==========================================
            self.dlg.txtResult.append("▶ 대용량 관망/밸브 공간 인덱스 엔진 로드 중...")
            QCoreApplication.processEvents()
            
            # C++ 엔진을 이용한 초고속 스페이셜 인덱스 구축 (전체 데이터를 딕셔너리로 만들면 멈춤 현상 발생)
            valve_idx = QgsSpatialIndex(valve_layer.getFeatures())
            pipe_idx = QgsSpatialIndex(pipe_layer.getFeatures())

            found_valves = set()
            
            self.dlg.txtResult.append("▶ 관로 네트워크 추적(제수밸브 탐색) 시작...")
            QCoreApplication.processEvents()

            def get_endpoints(geom):
                """관로 양 끝점 반환"""
                if geom.isMultipart():
                    lines = geom.asMultiPolyline()
                    return [lines[0][0], lines[-1][-1]] if lines else []
                else:
                    line = geom.asPolyline()
                    return [line[0], line[-1]] if len(line) >= 2 else []

            def is_valve_ok(v_feat):
                """제수밸브 여부 확인 (이토/공기/소화전 제외)"""
                for attr in v_feat.attributes():
                    if attr:
                        s = str(attr).replace(" ", "")
                        if "이토" in s or "공기" in s or "소화" in s or "배기" in s:
                            return False
                return True

            SNAP_TOL = 1.0  # 끝점 연결 허용 오차 (m)
            from qgis.core import QgsGeometry as QgsGeo, QgsPointXY

            for start_pipe in crossing_pipes:
                start_geom = start_pipe.geometry()
                start_pts = get_endpoints(start_geom)

                # 시작 관로 자체의 바깥쪽 밸브 먼저 확인
                pipe_valve_ids = []
                cands = valve_idx.intersects(start_geom.boundingBox().scaled(1.2))
                for v_id in cands:
                    v_f = valve_layer.getFeature(v_id)
                    if not is_valve_ok(v_f):
                        continue
                    v_geom = v_f.geometry()
                    if v_geom and v_geom.distance(start_geom) < SNAP_TOL:
                        if not v_geom.within(block_geom):
                            pipe_valve_ids.append(v_id)

                if pipe_valve_ids:
                    # 시작 관로에 바깥쪽 밸브가 있으면 선택 완료, 추적 불필요
                    for v_id in pipe_valve_ids:
                        found_valves.add(v_id)
                    continue

                # 밸브 없으면 바깥쪽 끝점에서 토폴로지 연결 관로를 따라 탐색
                # queue : (pipe_id, 이 관로로 들어온 끝점)
                visited_pipes = {start_pipe.id()}
                queue = []

                for pt in start_pts:
                    pt_geom = QgsGeo.fromPointXY(QgsPointXY(pt))
                    if pt_geom.within(block_geom):
                        continue  # 블록 내부 방향 끝점은 무시
                    pt_bbox = QgsRectangle(pt.x()-SNAP_TOL, pt.y()-SNAP_TOL,
                                          pt.x()+SNAP_TOL, pt.y()+SNAP_TOL)
                    for n_id in pipe_idx.intersects(pt_bbox):
                        if n_id in visited_pipes:
                            continue
                        n_geom = pipe_layer.getFeature(n_id).geometry()
                        if not n_geom or n_geom.within(block_geom):
                            continue
                        # 끝점 실제 연결 확인
                        for npt in get_endpoints(n_geom):
                            if abs(npt.x()-pt.x()) < SNAP_TOL and abs(npt.y()-pt.y()) < SNAP_TOL:
                                visited_pipes.add(n_id)
                                queue.append((n_id, pt))
                                break

                while queue:
                    curr_id, entry_pt = queue.pop(0)
                    curr_pipe = pipe_layer.getFeature(curr_id)
                    if not curr_pipe or not curr_pipe.isValid():
                        continue
                    curr_geom = curr_pipe.geometry()
                    if not curr_geom:
                        continue

                    # 현재 관로의 바깥쪽 밸브 탐색
                    cands = valve_idx.intersects(curr_geom.boundingBox().scaled(1.2))
                    local_valves = []
                    for v_id in cands:
                        v_f = valve_layer.getFeature(v_id)
                        if not is_valve_ok(v_f):
                            continue
                        v_geom = v_f.geometry()
                        if v_geom and v_geom.distance(curr_geom) < SNAP_TOL:
                            if not v_geom.within(block_geom):
                                local_valves.append(v_f)

                    if local_valves:
                        # 밸브 발견 → 이 관로 경로는 차단 완료, 더 깊이 탐색 안 함
                        for v in local_valves:
                            found_valves.add(v.id())
                        continue

                    # 밸브 없음 → 반대쪽 끝점으로 이어진 관로 탐색 (들어온 방향 제외)
                    for pt in get_endpoints(curr_geom):
                        if abs(pt.x()-entry_pt.x()) < SNAP_TOL and abs(pt.y()-entry_pt.y()) < SNAP_TOL:
                            continue  # 들어온 방향은 역주행하지 않음
                        pt_geom = QgsGeo.fromPointXY(QgsPointXY(pt))
                        if pt_geom.within(block_geom):
                            continue  # 블록 내부로는 가지 않음
                        pt_bbox = QgsRectangle(pt.x()-SNAP_TOL, pt.y()-SNAP_TOL,
                                              pt.x()+SNAP_TOL, pt.y()+SNAP_TOL)
                        for n_id in pipe_idx.intersects(pt_bbox):
                            if n_id in visited_pipes:
                                continue
                            n_feat = pipe_layer.getFeature(n_id)
                            n_geom = n_feat.geometry()
                            if not n_geom or n_geom.within(block_geom):
                                continue
                            for npt in get_endpoints(n_geom):
                                if abs(npt.x()-pt.x()) < SNAP_TOL and abs(npt.y()-pt.y()) < SNAP_TOL:
                                    visited_pipes.add(n_id)
                                    queue.append((n_id, pt))
                                    break



            self.dlg.txtResult.append(f"<br><b style='color:green;'>[분석 완료]</b> 조작해야 할 제수밸브 수: <b>{len(found_valves)}</b>개")
            
            valve_layer.removeSelection() # 기존 노란색 선택 해제
            
            # 지도 캔버스에 시각적 하이라이트 (빨간색 점선 원형 마커)
            if found_valves:
                from qgis.core import QgsVectorLayer, QgsFeature, QgsMarkerSymbol, QgsUnitTypes, QgsProject
                from qgis.PyQt.QtCore import Qt
                from qgis.PyQt.QtGui import QColor
                
                # 1. 기존 강조 레이어 제거
                layer_name = "단수 대상 밸브(고립)"
                for layer in QgsProject.instance().mapLayersByName(layer_name):
                    QgsProject.instance().removeMapLayer(layer.id())

                # 2. 메모리 레이어 생성
                temp_layer = QgsVectorLayer("Point?crs=" + valve_layer.crs().authid(), layer_name, "memory")
                pr = temp_layer.dataProvider()
                
                # 3. 피처 복사
                new_feats = []
                for v_id in found_valves:
                    v_feat = valve_layer.getFeature(v_id)
                    new_feat = QgsFeature()
                    new_feat.setGeometry(v_feat.geometry())
                    new_feats.append(new_feat)
                pr.addFeatures(new_feats)
                
                # 4. 심볼 스타일링 (원형 도형 / 내부 투명 / 외부 빨간색 점선 / 굵기 2pt)
                symbol = QgsMarkerSymbol.createSimple({'name': 'circle', 'color': '0,0,0,0'})
                symbol_layer = symbol.symbolLayer(0)
                
                symbol_layer.setFillColor(QColor(0, 0, 0, 0)) # 내부 투명
                symbol_layer.setStrokeColor(QColor(255, 0, 0)) # 외부 빨간색
                symbol_layer.setStrokeStyle(Qt.DashLine) # 점선 스타일
                
                symbol_layer.setStrokeWidthUnit(QgsUnitTypes.RenderPoints)
                symbol_layer.setStrokeWidth(2.0) # 굵기 2pt
                
                symbol_layer.setSizeUnit(QgsUnitTypes.RenderPoints)
                symbol_layer.setSize(18.0) # 밸브 아이콘을 감쌀 만큼 넉넉한 사이즈

                temp_layer.renderer().setSymbol(symbol)
                
                # 5. 프로젝트에 추가
                QgsProject.instance().addMapLayer(temp_layer)

                self.dlg.txtResult.append(f"지도 상에 차단 대상 밸브가 <span style='color:red;'><b>빨간색 점선 원형</b></span>으로 표기되었습니다!")
                
                # Phase 5: 결과 저장 및 내보내기 버튼 활성화
                self._found_valves = found_valves
                self._last_block_name = block_name
                self._valve_layer = valve_layer
                self.dlg.btnExport.setEnabled(True)
                self.dlg.txtResult.append("<br><i>💡 '작업 지시서 내보내기' 버튼을 눌러 CSV 파일을 생성할 수 있습니다.</i>")
            else:
                self.dlg.txtResult.append("<span style='color:red;'>차단할 수 있는 밸브를 찾지 못했습니다. (관망 단절 또는 밸브 누락 의심)</span>")
                self.dlg.btnExport.setEnabled(False)

        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            self.dlg.txtResult.append(f"<br><span style='color:red;'><b>치명적 오류 발생:</b><br>{str(e)}</span>")
            print(err_msg)

    def on_export_clicked(self):
        """Phase 5: 작업 지시서 CSV 내보내기"""
        import csv
        import os
        from datetime import datetime
        from qgis.PyQt.QtWidgets import QFileDialog

        if not self._found_valves or not self._valve_layer:
            QMessageBox.warning(self.dlg, "경고", "먼저 분석을 실행하여 결과를 생성하세요.")
            return

        # 저장 경로 선택
        now_str = datetime.now().strftime("%Y%m%d_%H%M")
        default_name = f"단수작업지시서_{self._last_block_name}_{now_str}.csv"
        save_path, _ = QFileDialog.getSaveFileName(
            self.dlg, "작업 지시서 저장", default_name, "CSV 파일 (*.csv)"
        )
        if not save_path:
            return

        try:
            # 밸브 레이어 속성 필드명 수집
            field_names = [f.name() for f in self._valve_layer.fields()]

            with open(save_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 헤더: 작업 정보
                writer.writerow(["[단수 작업 지시서]"])
                writer.writerow([f"대상 블록", self._last_block_name])
                writer.writerow([f"작성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([f"차단 대상 밸브 수", len(self._found_valves)])
                writer.writerow([])

                # 밸브 속성 테이블 헤더
                writer.writerow(["No."] + field_names + ["X좌표", "Y좌표", "작업상태"])

                # 밸브별 데이터 행
                for idx, v_id in enumerate(self._found_valves, 1):
                    v_feat = self._valve_layer.getFeature(v_id)
                    attrs = [str(a) if a is not None else '' for a in v_feat.attributes()]
                    geom = v_feat.geometry()
                    pt = geom.asPoint()
                    x_coord = f"{pt.x():.4f}" if geom else ''
                    y_coord = f"{pt.y():.4f}" if geom else ''
                    writer.writerow([idx] + attrs + [x_coord, y_coord, "미완료"])

            QMessageBox.information(
                self.dlg, "완료",
                f"작업 지시서가 저장되었습니다!\n{save_path}"
            )
            self.dlg.txtResult.append(f"<br><b style='color:green;'>✅ 작업 지시서 저장 완료:</b> {os.path.basename(save_path)}")

        except Exception as e:
            import traceback
            QMessageBox.critical(self.dlg, "저장 오류", str(e))
            print(traceback.format_exc())
