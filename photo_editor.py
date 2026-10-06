"""
Простой фоторедактор.
Вариант 4: Фоторедактор с регулировкой интенсивности размытия (QSlider).
"""

import os
import sys

import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QSlider, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt


class PhotoEditor(QMainWindow):
    """Фоторедактор с гауссовым размытием и регулировкой радиуса."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Фоторедактор — размытие с регулировкой интенсивности")
        self.setGeometry(100, 100, 800, 650)

        self.current_image = None    # Исходное загруженное изображение (BGR, numpy array)
        self.processed_image = None  # Результат применения фильтра (то, что сохраняем)

        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""

        # --- Область отображения изображения ---
        self.image_label = QLabel("Загрузите изображение")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(700, 450)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")

        # --- Кнопка загрузки ---
        self.load_button = QPushButton("Загрузить изображение")
        self.load_button.clicked.connect(self.load_image)

        # --- Слайдер интенсивности размытия ---
        self.blur_label = QLabel("Интенсивность размытия: 0")
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(25)
        self.blur_slider.setValue(0)
        self.blur_slider.setEnabled(False)
        self.blur_slider.valueChanged.connect(self.update_filter)

        # --- Кнопки сброса и сохранения ---
        self.reset_button = QPushButton("Сбросить")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_image)

        self.save_button = QPushButton("Сохранить")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_image)

        # --- Компоновка ---
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.blur_label)
        slider_layout.addWidget(self.blur_slider)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.load_button)
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addLayout(slider_layout)
        layout.addLayout(buttons_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_image(self):
        """Загрузка изображения через диалог выбора файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "",
            "Изображения (*.jpg *.jpeg *.png *.bmp)"
        )

        if not file_path:
            return

        image = cv2.imread(file_path)

        if image is None:
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить изображение.\n"
                                                   "Проверьте, что файл существует и формат поддерживается.")
            return

        self.current_image = image
        self.processed_image = image.copy()

        # Сбрасываем слайдер и включаем управление
        self.blur_slider.blockSignals(True)
        self.blur_slider.setValue(0)
        self.blur_slider.blockSignals(False)
        self.blur_label.setText("Интенсивность размытия: 0")

        self.blur_slider.setEnabled(True)
        self.reset_button.setEnabled(True)
        self.save_button.setEnabled(True)

        self.display_image(self.processed_image)

    def update_filter(self, value: int):
        """Применение размытия при изменении значения слайдера."""
        if self.current_image is None:
            return

        self.blur_label.setText(f"Интенсивность размытия: {value}")

        if value == 0:
            # При значении 0 размытие не применяется — показываем оригинал
            self.processed_image = self.current_image.copy()
        else:
            radius = value * 2 + 1  # Ядро гауссова размытия должно быть нечётным
            self.processed_image = cv2.GaussianBlur(self.current_image, (radius, radius), 0)

        self.display_image(self.processed_image)

    def display_image(self, image):
        """Отображение изображения (numpy array, BGR) в QLabel."""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        h, w, channels = rgb_image.shape
        bytes_per_line = channels * w

        # Копируем данные, чтобы избежать проблем с временным буфером numpy
        qimage = QImage(
            rgb_image.data, w, h, bytes_per_line,
            QImage.Format.Format_RGB888
        ).copy()

        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.width(), self.image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def reset_image(self):
        """Сброс размытия и возврат к оригинальному изображению."""
        if self.current_image is None:
            return

        self.blur_slider.blockSignals(True)
        self.blur_slider.setValue(0)
        self.blur_slider.blockSignals(False)
        self.blur_label.setText("Интенсивность размытия: 0")

        self.processed_image = self.current_image.copy()
        self.display_image(self.processed_image)

    def save_image(self):
        """Сохранение обработанного изображения через диалог."""
        if self.processed_image is None:
            QMessageBox.warning(self, "Внимание", "Нет изображения для сохранения.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить изображение", "result.jpg",
            "JPEG (*.jpg *.jpeg);;PNG (*.png);;BMP (*.bmp)"
        )

        if not file_path:
            return

        try:
            success = cv2.imwrite(file_path, self.processed_image)
            if success:
                QMessageBox.information(self, "Готово", f"Изображение сохранено:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить изображение.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {e}")


def main():
    app = QApplication(sys.argv)
    window = PhotoEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
