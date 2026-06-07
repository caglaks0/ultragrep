import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import threading

# Doğrudan import (göreceli import yerine)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ultragrep import searcher

class SearchWorker(QThread):
    """Arama işlemini arka planda yürüten thread"""
    result_found = pyqtSignal(str, int, str)
    search_finished = pyqtSignal(int, float)
    status_update = pyqtSignal(str)
    
    def __init__(self, pattern, search_path):
        super().__init__()
        self.pattern = pattern
        self.search_path = search_path
        
    def run(self):
        import time
        start_time = time.time()
        count = 0
        
        for file_path, line_num, line, scope, scope_type in searcher.search(self.pattern, self.search_path):
            # Dosya yolunu kısalt
            rel_path = os.path.relpath(file_path, self.search_path)
            scope_str = f" [{scope_type}: {scope}]" if scope else ""
            scope_str = f" [fonksiyon: {scope}]" if scope else ""
            self.result_found.emit(rel_path, line_num, line.strip() + scope_str)
            count += 1
            QApplication.processEvents()
        
        elapsed = time.time() - start_time
        self.search_finished.emit(count, elapsed)


class ReplaceWorker(QThread):
    """Değiştirme işlemini arka planda yürüten thread"""
    result_found = pyqtSignal(str, int, str, str)
    replace_finished = pyqtSignal(int, float)
    status_update = pyqtSignal(str)
    
    def __init__(self, pattern, replacement, search_path, dry_run):
        super().__init__()
        self.pattern = pattern
        self.replacement = replacement
        self.search_path = search_path
        self.dry_run = dry_run
        
    def run(self):
        import time
        start_time = time.time()
        
        total_changes, changes = searcher.replace(
            self.pattern, self.replacement, self.search_path, self.dry_run
        )
        
        for file_path, file_changes in changes:
            rel_path = os.path.relpath(file_path, self.search_path)
            for line_num, old_text, new_text in file_changes:
                self.result_found.emit(rel_path, line_num, old_text, new_text)
                QApplication.processEvents()
        
        elapsed = time.time() - start_time
        self.replace_finished.emit(total_changes, elapsed)


class UltraGrepGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.search_worker = None
        self.replace_worker = None
        self.init_ui()
        self.apply_styles()
        
    def init_ui(self):
        # Ana widget ve layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        central_widget.setLayout(main_layout)
        
        # ===== BAŞLIK =====
        title_label = QLabel("UltraGrep Professional")
        title_font = QFont("Segoe UI", 18, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # ===== ARAMA BÖLÜMÜ =====
        search_group = QGroupBox("Arama Yap")
        search_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        search_layout = QVBoxLayout()
        search_layout.setSpacing(12)
        search_layout.setContentsMargins(15, 20, 15, 15)
        
        # Aranacak kelime
        pattern_layout = QHBoxLayout()
        pattern_label = QLabel("Aranacak Kelime:")
        pattern_label.setMinimumWidth(120)
        pattern_label.setFont(QFont("Segoe UI", 10))
        self.search_pattern_input = QLineEdit()
        self.search_pattern_input.setPlaceholderText("Örnek: merhaba, test, deneme")
        self.search_pattern_input.setMinimumHeight(35)
        self.search_pattern_input.setFont(QFont("Segoe UI", 10))
        pattern_layout.addWidget(pattern_label)
        pattern_layout.addWidget(self.search_pattern_input)
        search_layout.addLayout(pattern_layout)
        
        # Dizin seçimi
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Aranacak Dizin:")
        dir_label.setMinimumWidth(120)
        dir_label.setFont(QFont("Segoe UI", 10))
        self.dir_input = QLineEdit()
        self.dir_input.setText(os.getcwd())
        self.dir_input.setMinimumHeight(35)
        self.dir_input.setFont(QFont("Segoe UI", 10))
        self.browse_btn = QPushButton("Gözat...")
        self.browse_btn.setMinimumHeight(35)
        self.browse_btn.setMinimumWidth(80)
        self.browse_btn.setFont(QFont("Segoe UI", 10))
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        search_layout.addLayout(dir_layout)
        
        # Arama butonu
        self.search_btn = QPushButton("Aramayı Başlat")
        self.search_btn.setMinimumHeight(45)
        self.search_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.search_btn.clicked.connect(self.start_search)
        search_layout.addWidget(self.search_btn)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # ===== DEĞİŞTİRME BÖLÜMÜ =====
        replace_group = QGroupBox("Değiştirme Yap")
        replace_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        replace_layout = QVBoxLayout()
        replace_layout.setSpacing(12)
        replace_layout.setContentsMargins(15, 20, 15, 15)
        
        # Eski kelime
        old_layout = QHBoxLayout()
        old_label = QLabel("Eski Kelime:")
        old_label.setMinimumWidth(120)
        old_label.setFont(QFont("Segoe UI", 10))
        self.old_pattern_input = QLineEdit()
        self.old_pattern_input.setPlaceholderText("Değiştirilecek kelime...")
        self.old_pattern_input.setMinimumHeight(35)
        self.old_pattern_input.setFont(QFont("Segoe UI", 10))
        old_layout.addWidget(old_label)
        old_layout.addWidget(self.old_pattern_input)
        replace_layout.addLayout(old_layout)
        
        # Yeni kelime
        new_layout = QHBoxLayout()
        new_label = QLabel("Yeni Kelime:")
        new_label.setMinimumWidth(120)
        new_label.setFont(QFont("Segoe UI", 10))
        self.new_pattern_input = QLineEdit()
        self.new_pattern_input.setPlaceholderText("Yeni kelime...")
        self.new_pattern_input.setMinimumHeight(35)
        self.new_pattern_input.setFont(QFont("Segoe UI", 10))
        new_layout.addWidget(new_label)
        new_layout.addWidget(self.new_pattern_input)
        replace_layout.addLayout(new_layout)
        
        # Seçenekler
        options_layout = QHBoxLayout()
        self.dry_run_check = QCheckBox("Önizleme Modu (değişiklik yapmadan göster)")
        self.dry_run_check.setFont(QFont("Segoe UI", 10))
        options_layout.addWidget(self.dry_run_check)
        options_layout.addStretch()
        replace_layout.addLayout(options_layout)
        
        # Değiştir butonu
        self.replace_btn = QPushButton("Değiştirmeyi Başlat")
        self.replace_btn.setMinimumHeight(45)
        self.replace_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.replace_btn.clicked.connect(self.start_replace)
        replace_layout.addWidget(self.replace_btn)
        
        replace_group.setLayout(replace_layout)
        main_layout.addWidget(replace_group)
        
        # ===== İLERLEME ÇUBUĞU =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setFont(QFont("Segoe UI", 10))
        main_layout.addWidget(self.progress_bar)
        
        # ===== DURUM ÇUBUĞU =====
        self.status_label = QLabel("Hazır")
        self.status_label.setMinimumHeight(30)
        self.status_label.setFont(QFont("Segoe UI", 10))
        main_layout.addWidget(self.status_label)
        
        # ===== SONUÇLAR BÖLÜMÜ =====
        results_group = QGroupBox("Sonuçlar")
        results_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        results_layout = QVBoxLayout()
        results_layout.setSpacing(8)
        
        # Sonuç ağacı (SCROLLBAR EKLENDİ)
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Dosya Yolu", "Satır No", "İçerik"])
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setIndentation(15)
        self.results_tree.itemDoubleClicked.connect(self.open_file_at_line)
        
        # Scrollbar'ları aktif et
        self.results_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.results_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Stil ayarları
        self.results_tree.setFont(QFont("Consolas", 9))
        self.results_tree.setMinimumHeight(350)
        
        # Header genişlikleri
        self.results_tree.setColumnWidth(0, 450)
        self.results_tree.setColumnWidth(1, 70)
        self.results_tree.setColumnWidth(2, 600)
        
        # Butonlar ve sayaç
        bottom_bar = QHBoxLayout()
        self.clear_btn = QPushButton("Sonuçları Temizle")
        self.clear_btn.clicked.connect(self.clear_results)
        self.clear_btn.setMinimumHeight(35)
        self.clear_btn.setFont(QFont("Segoe UI", 10))
        
        self.result_count_label = QLabel("0 sonuç")
        self.result_count_label.setAlignment(Qt.AlignRight)
        self.result_count_label.setMinimumHeight(35)
        self.result_count_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        
        bottom_bar.addWidget(self.clear_btn)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.result_count_label)
        
        results_layout.addWidget(self.results_tree)
        results_layout.addLayout(bottom_bar)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        # Pencere boyutunu ayarla
        self.setWindowTitle("UltraGrep Professional - Arama ve Değiştirme Aracı")
        self.setGeometry(50, 50, 1300, 800)
        self.setMinimumSize(1000, 600)
        
    def apply_styles(self):
        """Modern koyu tema stilleri (daha az parlak)"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #181825;
                color: #cdd6f4;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #89b4fa;
            }
            
            QLabel {
                color: #cdd6f4;
                font-size: 11px;
                font-weight: 500;
            }
            
            QLineEdit {
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                background-color: #313244;
                color: #cdd6f4;
            }
            
            QLineEdit:focus {
                border: 1px solid #89b4fa;
                background-color: #45475a;
            }
            
            QLineEdit::placeholder {
                color: #6c7086;
            }
            
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 6px 20px;
                font-size: 11px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #6c9fdf;
            }
            
            QPushButton:pressed {
                background-color: #4c7ab3;
            }
            
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
            
            QTreeWidget {
                border: 1px solid #313244;
                border-radius: 6px;
                background-color: #181825;
                alternate-background-color: #1e1e2e;
                color: #cdd6f4;
                font-size: 10px;
            }
            
            QTreeWidget::item {
                padding: 6px;
            }
            
            QTreeWidget::item:hover {
                background-color: #313244;
            }
            
            QTreeWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            
            QHeaderView::section {
                background-color: #313244;
                padding: 8px;
                border: none;
                font-weight: bold;
                color: #89b4fa;
                font-size: 11px;
            }
            
            QProgressBar {
                background-color: #313244;
                border: 1px solid #89b4fa;
                border-radius: 6px;
                text-align: center;
                color: #cdd6f4;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 5px;
            }
            
            QCheckBox {
                color: #cdd6f4;
                font-size: 11px;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #89b4fa;
                background-color: #313244;
            }
            
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border: 2px solid #89b4fa;
            }
            
            QCheckBox::indicator:hover {
                border: 2px solid #6c9fdf;
            }
            
            QScrollBar:vertical {
                background-color: #1e1e2e;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #89b4fa;
                border-radius: 6px;
                min-height: 30px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #6c9fdf;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                background-color: #1e1e2e;
                height: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: #89b4fa;
                border-radius: 6px;
                min-width: 30px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: #6c9fdf;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Status label stilini güncelle
        self.status_label.setStyleSheet("""
            background-color: #a6e3a1;
            color: #1e1e2e;
            padding: 8px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 13px;
        """)
        
    def show_confirmation_dialog(self, old_word, new_word):
        """Özelleştirilmiş, okunaklı onay diyaloğu"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Değişiklik Onayı")
        msg.setIcon(QMessageBox.Question)
        
        font = QFont("Segoe UI", 10)
        msg.setFont(font)
        
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #181825;
            }
            QLabel {
                color: #cdd6f4;
                background-color: #181825;
                font-size: 11px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #6c9fdf;
            }
        """)
        
        msg.setText(f"Kelime Değiştirme Onayı")
        msg.setInformativeText(f"\n'{old_word}' kelimesini '{new_word}' ile değiştirmek istediğinize emin misiniz?\n\nBu işlem GERİ ALINAMAZ!\n")
        
        yes_button = msg.addButton("Evet, Değiştir", QMessageBox.YesRole)
        no_button = msg.addButton("Hayır, İptal Et", QMessageBox.NoRole)
        
        msg.setMinimumWidth(450)
        reply = msg.exec_()
        return reply == QMessageBox.Yes
        
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Dizin Seç", self.dir_input.text())
        if directory:
            self.dir_input.setText(directory)
            
    def start_search(self):
        pattern = self.search_pattern_input.text()
        search_path = self.dir_input.text()
        
        if not pattern:
            QMessageBox.warning(self, "Uyarı", "Lütfen aramak istediğiniz kelimeyi girin!")
            return
            
        if not os.path.exists(search_path):
            QMessageBox.warning(self, "Uyarı", "Geçersiz dizin yolu!")
            return
            
        # UI'ı temizle ve devre dışı bırak
        self.clear_results()
        self.search_btn.setEnabled(False)
        self.replace_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Aranıyor... Lütfen bekleyin")
        
        # Arama işlemini başlat
        self.search_worker = SearchWorker(pattern, search_path)
        self.search_worker.result_found.connect(self.add_search_result)
        self.search_worker.search_finished.connect(self.search_finished)
        self.search_worker.status_update.connect(self.status_label.setText)
        self.search_worker.start()
        
    def add_search_result(self, file_path, line_num, line):
        item = QTreeWidgetItem([file_path, str(line_num), line])
        self.results_tree.addTopLevelItem(item)
        
        
        # Sonuç sayısını güncelle
        count = self.results_tree.topLevelItemCount()
        self.result_count_label.setText(f"{count} sonuç")
        
    def search_finished(self, count, elapsed):
        self.search_btn.setEnabled(True)
        self.replace_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if count == 0:
            self.status_label.setText("Arama tamamlandı - Hiçbir eşleşme bulunamadı")
            self.status_label.setStyleSheet("""
             background-color: #a6e3a1;
             color: #1e1e2e;
             padding: 8px;
             border-radius: 6px;
            font-weight: bold;
            font-size: 13px;
        """)
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Arama Sonucu")
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Arama Sonucu")
            msg.setInformativeText(f"'{self.search_pattern_input.text()}' kelimesi için hiçbir eşleşme bulunamadı.\n\nTarama süresi: {elapsed:.2f} saniye")
            msg.setStyleSheet("""
                QMessageBox { background-color: #181825; }
                QLabel { color: #cdd6f4; }
                QPushButton { background-color: #89b4fa; color: #1e1e2e; }
            """)
            msg.exec_()
        else:
            self.status_label.setText(f"Arama tamamlandı - {count} eşleşme bulundu")
            
    def start_replace(self):
        pattern = self.old_pattern_input.text()
        replacement = self.new_pattern_input.text()
        search_path = self.dir_input.text()
        dry_run = self.dry_run_check.isChecked()
        
        if not pattern:
            QMessageBox.warning(self, "Uyarı", "Lütfen değiştirilecek kelimeyi girin!")
            return
            
        if not os.path.exists(search_path):
            QMessageBox.warning(self, "Uyarı", "Geçersiz dizin yolu!")
            return
            
        # Onay
        if not dry_run:
            if not self.show_confirmation_dialog(pattern, replacement):
                return
        
        # UI'ı temizle ve devre dışı bırak
        self.clear_results()
        self.search_btn.setEnabled(False)
        self.replace_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Değiştirme işlemi yapılıyor...")
        
        # Değiştirme işlemini başlat
        self.replace_worker = ReplaceWorker(pattern, replacement, search_path, dry_run)
        self.replace_worker.result_found.connect(self.add_replace_result)
        self.replace_worker.replace_finished.connect(self.replace_finished)
        self.replace_worker.status_update.connect(self.status_label.setText)
        self.replace_worker.start()
        
    def add_replace_result(self, file_path, line_num, old_text, new_text):
        item = QTreeWidgetItem([file_path, str(line_num), f"{old_text}  →  {new_text}"])
        self.results_tree.addTopLevelItem(item)
        
    def replace_finished(self, count, elapsed):
        self.search_btn.setEnabled(True)
        self.replace_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        mode = "Önizleme" if self.dry_run_check.isChecked() else "Değiştirme"
        
        if count == 0:
            self.status_label.setText("Değiştirme tamamlandı - Hiçbir değişiklik yapılmadı")
        else:
            self.status_label.setText(f"{mode} tamamlandı - {count} değişiklik yapıldı")
            
            msg = QMessageBox(self)
            msg.setWindowTitle("İşlem Tamam")
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"{mode} Tamamlandı!")
            msg.setInformativeText(f"{count} değişiklik yapıldı.\nSüre: {elapsed:.2f} saniye")
            msg.setStyleSheet("""
                QMessageBox { background-color: #181825; }
                QLabel { color: #cdd6f4; }
                QPushButton { background-color: #89b4fa; color: #1e1e2e; }
            """)
            msg.exec_()
        
    def open_file_at_line(self, item, column):
        file_path = item.text(0)
        
        # Dosyayı varsayılan editörde aç
        import subprocess
        full_path = os.path.join(self.dir_input.text(), file_path)
        
        if sys.platform == "win32":
            subprocess.run(["notepad.exe", full_path])
        elif sys.platform == "darwin":
            subprocess.run(["open", full_path])
        else:
            subprocess.run(["xdg-open", full_path])
            
    def clear_results(self):
        self.results_tree.clear()
        self.result_count_label.setText("0 sonuç")
        self.status_label.setText("Hazır")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Yüksek DPI desteği
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = UltraGrepGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()