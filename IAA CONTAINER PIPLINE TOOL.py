# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
import maya.cmds as cmds
import os
import pathlib
import zipfile
import shutil

def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

# 自定义正方形标签（用于图片预览，保持正方形）
class SquareLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.setAlignment(QtCore.Qt.AlignCenter)
        # 关闭自动拉伸，防止图片撑破UI —— 关键修复
        self.setScaledContents(False)
        self.setText("图片预览")
        self.setStyleSheet("background-color: #f0f0f0;")
        # 固定最大尺寸，防止布局被破坏
        self.setMaximumSize(300, 300)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setFixedWidth(self.height())

# 自定义正方形文本浏览器（报错信息使用）
class SquareTextBrowser(QtWidgets.QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.setReadOnly(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setFixedWidth(self.height())

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        MainWindow.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # 主窗口中央部件
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        # 主布局（全局自适应）
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.mainLayout.setSpacing(8)

        # ========== 顶部：文件路径栏 ==========
        self.topLayout = QtWidgets.QHBoxLayout()
        self.topLayout.setSpacing(6)

        self.checkBox_topmost = QtWidgets.QCheckBox("PIN")
        self.checkBox_topmost.setChecked(True)
        self.topLayout.addWidget(self.checkBox_topmost)

        self.label = QtWidgets.QLabel("File Address:")
        self.lineEdit = QtWidgets.QLineEdit()
        self.pushButton = QtWidgets.QPushButton("Browse")
        self.pushButton_2 = QtWidgets.QPushButton("Import")
        self.pushButton_3 = QtWidgets.QPushButton("Export")
        self.pushButton_4 = QtWidgets.QPushButton("Automation")

        self.topLayout.addWidget(self.label)
        self.topLayout.addWidget(self.lineEdit, stretch=1)
        self.topLayout.addWidget(self.pushButton)
        self.topLayout.addWidget(self.pushButton_2)
        self.topLayout.addWidget(self.pushButton_3)
        self.topLayout.addWidget(self.pushButton_4)
        self.mainLayout.addLayout(self.topLayout)

        # ========== 内容区域：左侧 TreeWidget + 右侧面板 ==========
        self.contentLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.setSpacing(8)

        # 左侧：QTreeWidget 文件列表（改为树形表格，仿Windows）
        self.treeWidget = QtWidgets.QTreeWidget()
        self.treeWidget.setColumnCount(4)
        self.treeWidget.setHeaderLabels(["文件名", "类型", "大小", "修改时间"])
        self.treeWidget.setSortingEnabled(True)
        self.contentLayout.addWidget(self.treeWidget, stretch=3)

        # 右侧列布局
        self.rightLayout = QtWidgets.QVBoxLayout()
        self.rightLayout.setSpacing(6)

        # 进度显示标签
        self.label_completed = QtWidgets.QLabel("Completed：0%")
        self.label_completed.setAlignment(QtCore.Qt.AlignCenter)
        self.label_completed.setStyleSheet("font-size:14px; font-weight:bold; padding:5px;")

        # 报错信息显示区
        self.textBrowser_2 = SquareTextBrowser()
        # 图片预览区
        self.label_preview = SquareLabel()

        self.pushButton_6 = QtWidgets.QPushButton("Switch Display")

        self.rightLayout.addWidget(self.label_completed)
        self.rightLayout.addWidget(self.textBrowser_2)
        self.rightLayout.addWidget(self.label_preview)
        self.rightLayout.addWidget(self.pushButton_6)

        self.contentLayout.addLayout(self.rightLayout)
        self.mainLayout.addLayout(self.contentLayout, stretch=1)

        # ========== 菜单 + 状态栏 ==========
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("IAA CONTAINER PIPLINE TOOL")

class IaaContainerTool(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=get_maya_main_window()):
        super(IaaContainerTool, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.Window)

        # 默认置顶
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        # 绑定信号
        self.checkBox_topmost.toggled.connect(self.toggle_topmost)
        self.pushButton.clicked.connect(self.browse_folder)
        self.pushButton_2.clicked.connect(self.import_zip_files)
        self.pushButton_3.clicked.connect(self.export_models)
        self.pushButton_4.clicked.connect(self.run_automation)
        # 新增：列表点击加载预览图
        self.treeWidget.itemClicked.connect(self.load_preview_from_tree)

        # ===================== 新增：地址栏输入回车加载路径 =====================
        self.lineEdit.returnPressed.connect(self.load_path_from_lineedit)

    # 切换窗口置顶
    def toggle_topmost(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        self.show()

    # ===================== 新增：从地址栏手动加载路径 =====================
    def load_path_from_lineedit(self):
        input_path = self.lineEdit.text().strip()
        if not input_path or not os.path.isdir(input_path):
            self.textBrowser_2.append("<span style='color:red'>路径无效，请输入正确的文件夹路径</span>")
            self.statusbar.showMessage("路径无效", 2000)
            return

        # 加载目录
        self.show_file_info_in_tree(input_path)
        self.statusbar.showMessage(f"已加载路径：{input_path}", 3000)

    # ===================== 新增：自动加载匹配的预览图 =====================
    def load_preview_from_tree(self):
        """从文件列表点击加载预览图"""
        item = self.treeWidget.currentItem()
        if not item:
            return
        root = self.lineEdit.text().strip()
        name = item.text(0)
        path = os.path.join(root, name)
        self.auto_load_preview(path)

    def auto_load_preview(self, select_path):
        """
        自动匹配预览图：
        1. 选择 CE_Ae86Sedan 文件夹 → 加载 CE_Ae86Sedan_Preview.png
        2. 选择 CE_Ae86Sedan_Model.fbx → 加载 CE_Ae86Sedan_Preview.png
        """
        try:
            preview_img = None

            if os.path.isdir(select_path):
                # 选择的是文件夹
                folder_name = os.path.basename(select_path)
                model_sub = os.path.join(select_path, "Model")
                if os.path.exists(model_sub):
                    preview_img = os.path.join(model_sub, f"{folder_name}_Preview.png")
                else:
                    preview_img = os.path.join(select_path, f"{folder_name}_Preview.png")

            elif os.path.isfile(select_path) and select_path.lower().endswith(".fbx"):
                # 选择的是FBX文件
                file_name = os.path.splitext(os.path.basename(select_path))[0]
                folder = os.path.dirname(select_path)
                if file_name.endswith("_Model"):
                    base = file_name.replace("_Model", "")
                    preview_img = os.path.join(folder, f"{base}_Preview.png")

            self.show_image(preview_img)

        except:
            self.label_preview.setText("预览图错误")

    # ===================== 最终完整版 Automation（含精准UV展开 + 预览图重命名） =====================
    def run_automation(self):
        try:
            self.textBrowser_2.append("=" * 60)
            self.textBrowser_2.append("开始执行 Automation 自动化流程...")
            QtCore.QCoreApplication.processEvents()

            # 只获取网格模型物体（过滤相机、灯光、曲线等）
            all_meshes = cmds.ls(type="mesh", long=True)
            if not all_meshes:
                self.textBrowser_2.append("<span style='color:orange'>场景中没有可操作网格模型</span>")
                return

            # 获取transform父物体
            mesh_transforms = []
            for mesh in all_meshes:
                trans = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
                if trans not in mesh_transforms:
                    mesh_transforms.append(trans)

            cmds.select(mesh_transforms, replace=True)
            self.textBrowser_2.append(f"<span style='color:green'>已识别模型数量：{len(mesh_transforms)}</span>")
            QtCore.QCoreApplication.processEvents()

            mat_count = 0
            hard_edge_count = 0
            uv_count = 0
            freeze_count = 0
            history_count = 0
            rename_count = 0  # 成功重命名的预览图数量

            root_path = self.lineEdit.text().strip()  # 获取根目录

            # 单个物体遍历执行，杜绝多对象报错
            for trans in mesh_transforms:
                short_name = cmds.ls(trans, shortNames=True)[0]

                # 1. 全部边设为硬边（单物体执行）
                cmds.polySoftEdge(trans, angle=0)
                hard_edge_count += 1

                # 2. 【精准按照你要求的参数】自动展UV到第一象限
                cmds.polyAutoProjection(
                    trans,
                    planes=6,            # 平面：6
                    optimize=1,          # 优化：较少的片数
                    layout=2,            # 壳布局（置于方形）
                    scaleMode=1,         # 比例模式：一致
                    layoutMethod=0,      # 壳堆叠：边界盒
                    percentageSpace=0.1, # 百分比间距：0.1
                    projectBothDirections=False,
                    worldSpace=False
                )
                uv_count += 1

                # 3. 材质命名：CE_Wine_Model → CE_Wine_M
                if short_name.endswith("_Model"):
                    mat_name = short_name.replace("_Model", "_M")
                else:
                    mat_name = short_name + "_M"

                # 创建Lambert材质+着色器组
                if not cmds.objExists(mat_name):
                    sg_name = mat_name + "_SG"
                    cmds.shadingNode("lambert", asShader=True, name=mat_name)
                    cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg_name)
                    cmds.connectAttr(f"{mat_name}.outColor", f"{sg_name}.surfaceShader", force=True)

                # 赋予材质
                sg = mat_name + "_SG"
                cmds.sets(trans, edit=True, forceElement=sg)
                mat_count += 1

                # 4. 冻结变换（单物体）
                cmds.makeIdentity(trans, apply=True, t=True, r=True, s=True)
                freeze_count += 1

                # 5. 删除历史（单物体）
                cmds.delete(trans, ch=True)
                history_count += 1

                # ========== 新增：重命名预览图 ==========
                if short_name.endswith("_Model"):
                    base_name = short_name.replace("_Model", "")  # 如 CE_Wine
                    src_png = os.path.join(root_path, f"{base_name}.png")
                    dst_png = os.path.join(root_path, f"{base_name}_Preview.png")
                    try:
                        if os.path.isfile(src_png):
                            # 如果目标已存在，可选择跳过或覆盖，这里直接覆盖
                            if os.path.exists(dst_png):
                                os.remove(dst_png)
                                self.textBrowser_2.append(f"<span style='color:orange'>已覆盖已存在的预览图：{os.path.basename(dst_png)}</span>")
                            os.rename(src_png, dst_png)
                            self.textBrowser_2.append(f"<span style='color:green'>预览图已重命名：{os.path.basename(src_png)} → {os.path.basename(dst_png)}</span>")
                            rename_count += 1
                        else:
                            self.textBrowser_2.append(f"<span style='color:orange'>未找到预览图：{base_name}.png，跳过重命名</span>")
                    except Exception as e:
                        self.textBrowser_2.append(f"<span style='color:red'>重命名预览图失败：{base_name}.png | 错误：{str(e)}</span>")
                # ======================================

            # 日志汇总
            self.textBrowser_2.append(f"<span style='color:green'>硬边设置完成：{hard_edge_count} 个</span>")
            self.textBrowser_2.append(f"<span style='color:green'>UV自动展开&第一象限排布完成：{uv_count} 个</span>")
            self.textBrowser_2.append(f"<span style='color:green'>材质创建&赋予完成：{mat_count} 个</span>")
            self.textBrowser_2.append(f"<span style='color:green'>冻结变换完成：{freeze_count} 个</span>")
            self.textBrowser_2.append(f"<span style='color:green'>删除历史完成：{history_count} 个</span>")
            self.textBrowser_2.append(f"<span style='color:green'>预览图重命名完成：{rename_count} 个</span>")

            self.textBrowser_2.append("Automation 全部执行完成！")
            self.textBrowser_2.append("=" * 60)
            self.statusbar.showMessage("Automation 执行完成", 5000)
            cmds.select(clear=True)

        except Exception as e:
            self.textBrowser_2.append(f"<span style='color:red'>Automation 出错：{str(e)}</span>")

    # ===================== 【已修改】Export 功能：自动识别CE/SE/CR 分类导出 =====================
    def export_models(self):
        try:
            self.textBrowser_2.append("=" * 60)
            self.textBrowser_2.append("开始执行模型导出 Export...")
            QtCore.QCoreApplication.processEvents()

            root_path = self.lineEdit.text().strip()
            if not root_path or not os.path.isdir(root_path):
                self.textBrowser_2.append("<span style='color:red'>错误：请先通过 Browse 选择有效文件夹！</span>")
                return

            # 1. 创建主目录结构
            model_root = os.path.join(root_path, "Model")
            collectible = os.path.join(model_root, "Collectible_Model")
            scene = os.path.join(model_root, "Scene_Model")
            character = os.path.join(model_root, "Character_Model")

            for folder in [collectible, scene, character]:
                os.makedirs(folder, exist_ok=True)

            # 2. 获取所有模型
            all_meshes = cmds.ls(type="mesh", long=True)
            if not all_meshes:
                self.textBrowser_2.append("<span style='color:red'>场景中没有可导出网格模型</span>")
                return

            mesh_transforms = []
            for mesh in all_meshes:
                trans = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
                mesh_transforms.append(trans)

            total = len(mesh_transforms)
            success = 0

            # 3. 遍历导出每个模型
            for i, trans in enumerate(mesh_transforms):
                short_name = cmds.ls(trans, shortNames=True)[0]

                # ===================== 核心：自动判断模型类型（CE/SE/CR） =====================
                if short_name.startswith("CE_"):
                    target_root = collectible
                    self.textBrowser_2.append(f"识别为道具模型：{short_name}")
                elif short_name.startswith("SE_"):
                    target_root = scene
                    self.textBrowser_2.append(f"识别为场景模型：{short_name}")
                elif short_name.startswith("CR_"):
                    target_root = character
                    self.textBrowser_2.append(f"识别为角色模型：{short_name}")
                else:
                    target_root = collectible
                    self.textBrowser_2.append(f"<span style='color:orange'>未识别前缀，默认归类为道具：{short_name}</span>")

                # ===================== 统一命名规则 =====================
                if short_name.endswith("_Model"):
                    folder_name = short_name.replace("_Model", "")
                else:
                    folder_name = short_name

                fbx_file_name = short_name
                preview_file_name = folder_name

                # 4. 创建统一标准目录结构（所有类型模型结构完全一致）
                item_folder = os.path.join(target_root, folder_name)
                sub_model = os.path.join(item_folder, "Model")
                sub_tex = os.path.join(item_folder, "Texture")
                sub_shader = os.path.join(item_folder, "Shader")
                sub_anim = os.path.join(item_folder, "Animation")

                for f in [sub_model, sub_tex, sub_shader, sub_anim]:
                    os.makedirs(f, exist_ok=True)

                # 5. FBX 导出路径
                fbx_path = os.path.join(sub_model, f"{fbx_file_name}.fbx")

                # 6. 选中并导出 FBX
                cmds.select(trans, replace=True)

                fbx_options = (
                    "fbx;2020;smoothing=none;animation=0;"
                    "blendShapes=0;skins=0;cameras=0;lights=0;"
                    "normals=1;uvs=1;materials=1"
                )

                cmds.file(
                    fbx_path,
                    force=True,
                    type="FBX export",
                    exportSelected=True,
                    options=fbx_options,
                    preserveReferences=False
                )

                # 7. 自动复制对应预览图
                preview_src = os.path.join(root_path, f"{preview_file_name}_Preview.png")
                preview_dst = os.path.join(sub_model, f"{preview_file_name}_Preview.png")

                if os.path.exists(preview_src):
                    shutil.copy2(preview_src, preview_dst)
                    self.textBrowser_2.append(f"<span style='color:green'>预览图已复制：{preview_file_name}_Preview.png</span>")
                else:
                    self.textBrowser_2.append(f"<span style='color:orange'>未找到预览图：{preview_file_name}_Preview.png</span>")

                self.textBrowser_2.append(f"<span style='color:green'>导出完成：{short_name}.fbx</span>")
                success += 1

                # 进度
                progress = int((i + 1) / total * 100)
                self.set_progress(progress)
                QtCore.QCoreApplication.processEvents()

            cmds.select(clear=True)
            self.textBrowser_2.append(f"<span style='color:green'>导出全部完成：成功 {success}/{total}</span>")
            self.statusbar.showMessage("Export 完成", 5000)

        except Exception as e:
            self.textBrowser_2.append(f"<span style='color:red'>Export 出错：{str(e)}</span>")

    # ===================== Browse 核心功能（支持选择文件夹/FBX） =====================
    def browse_folder(self):
        self.lineEdit.clear()
        dialog = QtWidgets.QFileDialog(self)
        dialog.setWindowTitle("选择文件夹或FBX文件")
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setNameFilter("Files (*.fbx)")
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, "选择")

        if dialog.exec_():
            select_path = dialog.selectedFiles()[0]
            if not select_path:
                return

            # 自动设置根路径
            if os.path.isfile(select_path):
                root_path = os.path.dirname(select_path)
            else:
                root_path = select_path

            self.lineEdit.setText(root_path)
            self.show_file_info_in_tree(root_path)
            # 自动加载预览图
            self.auto_load_preview(select_path)

    def show_file_info_in_tree(self, folder_path):
        try:
            self.treeWidget.clear()
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                file_stat = os.stat(file_path)
                if os.path.isdir(file_path):
                    f_type = "文件夹"
                else:
                    f_type = pathlib.Path(file).suffix.upper() or "文件"

                size = file_stat.st_size
                if size >= 1024 * 1024:
                    size_str = f"{size / 1024 / 1024:.2f} MB"
                elif size >= 1024:
                    size_str = f"{size / 1024:.2f} KB"
                else:
                    size_str = f"{size} B"

                mtime = QtCore.QDateTime.fromSecsSinceEpoch(int(file_stat.st_mtime)).toString("yyyy-MM-dd hh:mm")
                item = QtWidgets.QTreeWidgetItem(self.treeWidget)
                item.setText(0, file)
                item.setText(1, f_type)
                item.setText(2, size_str)
                item.setText(3, mtime)

            self.statusbar.showMessage(f"加载成功：{folder_path}", 3000)
        except Exception as e:
            error = f"错误：{str(e)}"
            self.textBrowser_2.append(f"<span style='color:red'>{error}</span>")
            self.statusbar.showMessage(error, 3000)

    # ===================== 搜索文件夹下所有OBJ文件 =====================
    def find_all_obj_files(self, root_dir):
        obj_files = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for f in filenames:
                if f.lower().endswith(".obj"):
                    obj_files.append(os.path.join(dirpath, f))
        return obj_files

    # ===================== 导入OBJ到Maya（不创建Group） =====================
    def import_obj_to_maya(self, obj_path):
        try:
            cmds.file(
                obj_path,
                i=True,
                type="OBJ",
                ignoreVersion=True,
                mergeNamespacesOnClash=False,
                renamingPrefix="",
                options="mo=0",
                returnNewNodes=False
            )
            return True
        except Exception as e:
            return str(e)

    # ===================== Import 核心功能：解压ZIP + 导入OBJ =====================
    def import_zip_files(self):
        root_path = self.lineEdit.text().strip()
        if not root_path or not os.path.isdir(root_path):
            self.textBrowser_2.append("<span style='color:red'>错误：请先通过 Browse 选择有效文件夹！</span>")
            return

        zip_folder = os.path.join(root_path, "ZIP_Folder")
        if not os.path.exists(zip_folder):
            os.makedirs(zip_folder)

        zip_files = [f for f in os.listdir(root_path) if f.lower().endswith(".zip")]
        if not zip_files:
            self.textBrowser_2.append("<span style='color:orange'>提示：当前目录未找到任何 .zip 压缩文件</span>")
            return

        total = len(zip_files)
        success_unzip = 0
        for idx, zip_file in enumerate(zip_files):
            zip_name = os.path.splitext(zip_file)[0]
            zip_path = os.path.join(root_path, zip_file)
            extract_path = os.path.join(zip_folder, zip_name)

            try:
                if not os.path.exists(extract_path):
                    os.makedirs(extract_path)
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(extract_path)
                self.textBrowser_2.append(f"<span style='color:green'>成功解压：{zip_file}</span>")
                success_unzip += 1
            except Exception as e:
                self.textBrowser_2.append(f"<span style='color:red'>解压失败：{zip_file} | 错误：{str(e)}</span>")

            progress = int((idx + 1) / total * 100)
            self.set_progress(progress)
            QtCore.QCoreApplication.processEvents()

        self.textBrowser_2.append("-" * 50)
        self.textBrowser_2.append(f"解压完成：成功 {success_unzip}/{total} 个文件")
        self.textBrowser_2.append("开始导入 OBJ 模型到 Maya...")

        obj_list = self.find_all_obj_files(zip_folder)
        if not obj_list:
            self.textBrowser_2.append("<span style='color:orange'>未在解压目录中找到任何 OBJ 文件</span>")
            self.set_progress(100)
            return

        success_import = 0
        total_obj = len(obj_list)
        for i, obj in enumerate(obj_list):
            result = self.import_obj_to_maya(obj)
            if result is True:
                self.textBrowser_2.append(f"<span style='color:green'>导入成功：{os.path.basename(obj)}</span>")
                success_import += 1
            else:
                self.textBrowser_2.append(f"<span style='color:red'>导入失败：{os.path.basename(obj)} | {result}</span>")

            progress = int((i + 1) / total_obj * 100)
            self.set_progress(progress)
            QtCore.QCoreApplication.processEvents()

        self.textBrowser_2.append("-" * 50)
        self.textBrowser_2.append(f"全部任务完成：解压 {success_unzip}/{total} | 导入OBJ {success_import}/{total_obj}")
        self.statusbar.showMessage("Import 任务全部完成！", 5000)

    # ===================== 工具方法 =====================
    def set_progress(self, percent):
        self.label_completed.setText(f"Completed：{percent}%")

    def show_image(self, img_path):
        if img_path and os.path.exists(img_path):
            pix = QtGui.QPixmap(img_path)
            scaled_pix = pix.scaled(self.label_preview.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.label_preview.setPixmap(scaled_pix)
            self.statusbar.showMessage(f"已加载预览：{os.path.basename(img_path)}", 2000)
        else:
            self.label_preview.setText("无预览图")

# 启动工具（自动关闭旧窗口）
if __name__ == "__main__":
    try:
        iaa_tool.close()
        iaa_tool.deleteLater()
    except:
        pass
    iaa_tool = IaaContainerTool()
    iaa_tool.show()